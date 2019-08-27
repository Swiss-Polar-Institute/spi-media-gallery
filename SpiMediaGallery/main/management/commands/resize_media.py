import os
import sys
import tempfile
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone
from pymediainfo import MediaInfo

from ... import spi_s3_utils
from ... import utils
from ...models import Medium, MediumResized, File
from ...progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Resizes videos and photos to different sizes used by the application. ' \
           'Reads from different formats and the output format is JPEG or webm'

    def add_arguments(self, parser):
        parser.add_argument('media_type', type=str, choices=['Photos', 'Videos'], help='Resizes Photos or Videos')
        parser.add_argument('sizes_type', nargs='+', type=str,
                            help='Type of resizing (T for thumbnail, S for small, M for medium, L for large, O for original). Original changes the format to JPEG, potential rotation')

    def handle(self, *args, **options):
        bucket_name_media = 'original'
        bucket_name_resized = 'processed'
        media_type = options['media_type']
        sizes_type = options['sizes_type']

        for size in sizes_type:
            if size not in 'TSMLO':
                raise CommandError(
                    'Invalid size, needs to be T (Thumbnail), S (Small), M (Medium), L (Large) or O (Original)')

        resizer = Resizer(bucket_name_media, bucket_name_resized, sizes_type, media_type)

        resizer.resize_media()


def get_information_from_video(video_file: str) -> Dict[str, Any]:
    information: Dict[str, Any] = {}

    video_information = MediaInfo.parse(video_file)

    for track in video_information.tracks:
        if track.track_type == 'Video':
            information['width'] = track.width
            information['height'] = track.height
            information['duration'] = float(track.duration) / 1000
            if track.encoded_date is not None:
                dt = datetime.strptime(track.encoded_date, 'UTC %Y-%m-%d %H:%M:%S')
                dt = dt.replace(tzinfo=timezone.utc)
                information['date_encoded'] = dt

            else:
                information['date_encoded'] = None

    return information


class Resizer(object):
    _medium_type: str

    def __init__(self, bucket_name_media: str, bucket_name_resizes: str, sizes_type: List[str],
                 medium_type: str) -> None:
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._resizes_bucket = spi_s3_utils.SpiS3Utils(bucket_name_resizes)
        self._sizes_type = sizes_type

        if medium_type == 'Photos':
            self._medium_type = 'P'
        elif medium_type == 'Videos':
            self._medium_type = 'V'
        else:
            assert False

    @staticmethod
    def _update_information_from_photo_if_needed(photo: Medium, photo_file: str) -> None:
        """If photo has missing information (e.g. no width, height or datetime_taken)
        it will update the information reading it from param photo_file.

        :param photo: object to update the information to
        :param photo_file:  local file to extract the information from
        """
        if photo.width is None or photo.height is None or photo.datetime_taken is None:
            photo_information = utils.get_medium_information(photo_file)

            photo.width = photo_information['width']
            photo.height = photo_information['height']

            if 'datetime_taken' in photo_information:
                photo.datetime_taken = photo_information['datetime_taken']

            photo.save()

    @staticmethod
    def _update_information_from_video(video: Medium, video_file: str) -> None:
        """If param video has no width, height, duration or datetime_taken: it uses param video_file
        to read the information and update it

        :param video: object to update the information to
        :param video_file: file to extract the information from
        """
        if video.width is None or video.height is None or video.duration is None or video.datetime_taken is None:
            information = get_information_from_video(video_file)

            video.width = information['width']
            video.height = information['height']
            video.duration = information['duration']
            video.datetime_taken = information['date_encoded']

            video.save()

    def resize_media(self):
        already_resized = None
        for size_type in self._sizes_type:
            qs = MediumResized.objects.values_list('medium', flat=True).filter(size_label=size_type).filter(
                medium__medium_type=self._medium_type)

            if already_resized is None:
                already_resized = qs
            else:
                already_resized |= qs

        media_to_be_resized = Medium.objects.filter(medium_type=self._medium_type).exclude(id__in=already_resized)

        verbose = self._medium_type == Medium.VIDEO

        media_to_be_resized_count = media_to_be_resized.count()

        if media_to_be_resized_count == 0:
            print('Nothing to be resized? Aborting')
            sys.exit(1)

        if self._medium_type == Medium.PHOTO:
            total_steps = media_to_be_resized_count
            progress_report_unit = 'photos'
        else:
            total_steps = media_to_be_resized.aggregate(Sum('file__size'))['file__size__sum']
            progress_report_unit = None

        progress_report = ProgressReport(total_steps, unit=progress_report_unit,
                                         extra_information='Resizing medium to {}'.format(','.join(self._sizes_type)),
                                         steps_are_bytes=self._medium_type == Medium.VIDEO)

        for medium in media_to_be_resized:
            # Download Media file from the bucket
            print('Will resize: ', medium.file.object_storage_key)

            suffix = utils.file_extension(medium.file.object_storage_key)
            media_file = tempfile.NamedTemporaryFile(suffix='.' + suffix, delete=False)
            media_file.close()
            start_download = time.time()
            try:
                self._media_bucket.bucket().download_file(medium.file.object_storage_key, media_file.name)
            except ClientError:
                print('Cannot download: {}'.format(medium.file.object_storage_key))
                continue

            download_time = time.time() - start_download

            assert os.stat(media_file.name).st_size == medium.file.size

            if verbose:
                speed = (medium.file.size / 1024 / 1024) / download_time  # MB/s
                print('Download Stats. Size: {} Time: {} Speed: {:.2f} MB/s File: {}'.format(
                    utils.bytes_to_human_readable(medium.file.size),
                    utils.seconds_to_human_readable(download_time),
                    speed,
                    medium.file.object_storage_key))

            if medium.file.md5 is None:
                md5_media_file = utils.hash_of_file_path(media_file.name)
                medium.file.md5 = md5_media_file
                medium.file.save()

            self._resize_medium(medium, media_file.name, self._sizes_type)

            print('Finished: medium.id: {}'.format(medium.id))

            os.remove(media_file.name)

            if self._medium_type == Medium.PHOTO:
                progress_report.increment_and_print_if_needed()
            else:
                progress_report.increment_steps_and_print_if_needed(medium.file.size)

    def _resize_medium(self, medium, medium_local_file, sizes: List[str]):
        file_to_delete: Optional[str] = None

        file_resizer = ResizeMedium(medium, medium_local_file)

        if medium.medium_type == medium.PHOTO:
            self._update_information_from_photo_if_needed(medium, medium_local_file)
        elif medium.medium_type == medium.VIDEO:
            self._update_information_from_video(medium, medium_local_file)
        else:
            assert False

        for size_label in sizes:
            existing = MediumResized.objects.filter(medium=medium).filter(size_label=size_label)

            if existing.count() > 0:
                # It already exists, skip...
                continue

            if medium.file.size == 0:
                # File with size 0, skip...
                print('File {} size is 0, skipping'.format(medium.file.object_storage_key))
                continue

            file_resized, width, height = file_resizer.resize(size_label)

            if file_resized is None:
                print("Problem resizing file:", medium, "to:", size_label)
                continue

            md5_resized_file = utils.hash_of_file_path(file_resized)
            resized_file_extension = utils.file_extension(file_resized).lower()

            # Upload medium to bucket
            resized_key = os.path.join(settings.RESIZED_PREFIX,
                                       md5_resized_file + '-{}.{}'.format(size_label, resized_file_extension))

            self._resizes_bucket.upload_file(file_resized, resized_key)
            file_size = os.stat(file_resized).st_size

            os.remove(file_resized)

            # Adds new file in the database
            file = File()
            file.object_storage_key = resized_key
            file.md5 = md5_resized_file
            file.size = file_size
            file.bucket = File.PROCESSED
            file.save()

            # And the new resized medium
            resized_medium = MediumResized()
            resized_medium.file = file
            resized_medium.size_label = size_label
            resized_medium.height = height
            resized_medium.width = width
            resized_medium.medium = medium
            resized_medium.datetime_resized = datetime.now(tz=timezone.utc)
            resized_medium.save()

        if file_to_delete is not None:
            os.remove(file_to_delete)


class ResizeMedium:
    def __init__(self, medium, medium_local_file):
        self._medium = medium
        self._medium_local_file = medium_local_file
        self._file_pre_processed = None

    def __del__(self):
        if self._file_pre_processed is not None:
            os.remove(self._file_pre_processed)

    def resize(self, size_label: str):
        medium_type = self._medium.medium_type

        width = settings.IMAGE_LABEL_TO_SIZES[size_label][0]

        if medium_type == Medium.PHOTO:
            return self._resize_photo(width)
        elif medium_type == Medium.VIDEO:
            return self._resize_video(width)
        else:
            assert False

    def _resize_photo(self, width_wanted: int):
        file_extension = utils.file_extension(self._medium_local_file).lower()

        if (file_extension in settings.PHOTO_PRE_PROCESS_DCRAW) and self._file_pre_processed is None:
            self._file_pre_processed = utils.convert_raw_to_ppm(self._medium_local_file)

        if self._file_pre_processed is not None:
            file_to_resize = self._file_pre_processed
        else:
            file_to_resize = self._medium_local_file

        resized_medium_file = utils.resize_photo(file_to_resize, width_wanted)
        if os.stat(resized_medium_file).st_size == 0:
            print('File {} resized output size is 0, skipping it'.format(self._medium.file.object_storage_key))
            return None, None, None

        resized_image_information = utils.get_medium_information(resized_medium_file)
        width_wanted = resized_image_information['width']
        height = resized_image_information['height']
        return resized_medium_file, width_wanted, height

    def _resize_video(self, width_wanted: int):
        start_time = time.time()
        resized_medium_file = utils.resize_video(self._medium_local_file, width_wanted)
        if resized_medium_file is None:
            print('File {} cannot be encoded'.format(self._medium_local_file))
            return None, None, None

        duration_convert = time.time() - start_time
        information = get_information_from_video(resized_medium_file)
        if 'duration' in information:
            speed = information['duration'] / duration_convert

            print('Conversion took: {} Speed: {:.2f}x'.format(utils.seconds_to_human_readable(duration_convert),
                                                              speed))
        else:
            print('Conversion took: {} Speed: unknown, duration of video not known'.format(
                utils.seconds_to_human_readable(duration_convert)))

        width_wanted = height = None
        if 'width' in information and 'height' in information:
            width_wanted = information['width']
            height = information['height']

        return resized_medium_file, width_wanted, height
