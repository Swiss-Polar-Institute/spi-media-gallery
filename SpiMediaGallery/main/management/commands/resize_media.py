from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, MediumResized
from django.conf import settings
from PIL import Image
import sys
from django.utils import timezone

Image.MAX_IMAGE_PIXELS = None

import datetime
import tempfile
import os
from pymediainfo import MediaInfo
from django.db.models import Sum

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport

import time
from main import utils


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_media', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('bucket_name_resized', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('media_type', type=str, choices=["P", "V"], help="Resizes Photos or Videos")
        parser.add_argument('sizes_type', nargs="+", type=str, help="Type of resizing (T for thumbnail, S for small, M for medium, L for large, O for original). Original changes the format to JPEG, potential rotation")

    def handle(self, *args, **options):
        bucket_name_media = options["bucket_name_media"]
        bucket_name_resized = options["bucket_name_resized"]
        media_type = options['media_type']
        sizes_type = options["sizes_type"]

        for size in sizes_type:
            if size not in "TSMLO":
                print("Invalid size, needs to be T (Thumbnail), S (Small), M (Medium), L (Large) or O (Original)")
                sys.exit(1)

        resizer = Resizer(bucket_name_media, bucket_name_resized, sizes_type, media_type)

        resizer.resize_media()


def get_information_from_video(video_file):
    information = {}

    video_information = MediaInfo.parse(video_file)

    for track in video_information.tracks:
        if track.track_type == "Video":
            information['width'] = track.width
            information['height'] = track.height
            information['duration'] = float(track.duration) / 1000
            if track.encoded_date is not None:
                dt = datetime.datetime.strptime(track.encoded_date, "UTC %Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                information['date_encoded'] = dt

    return information


class Resizer(object):
    def __init__(self, bucket_name_media, bucket_name_resizes, sizes_type, medium_type):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._resizes_bucket = spi_s3_utils.SpiS3Utils(bucket_name_resizes)
        self._sizes_type = sizes_type
        self._medium_type = medium_type

    @staticmethod
    def _update_information_from_photo_if_needed(photo, photo_file):
        if photo.width is None or photo.height is None or photo.datetime_taken is None:
            media_photo = Image.open(photo_file)
            photo.width = media_photo.width
            photo.height = media_photo.height

            exif_data = media_photo.getexif()

            EXIF_DATE_ID = 36867

            if EXIF_DATE_ID in exif_data:
                try:
                    datetime_taken = datetime.datetime.strptime(exif_data[EXIF_DATE_ID], "%Y:%m:%d %H:%M:%S")
                    datetime_taken = datetime_taken.replace(tzinfo=timezone.UTC)
                except ValueError:
                    print("Invalid datetime:", exif_data[EXIF_DATE_ID], "in photo:", photo.id)
                    datetime_taken = None

                photo.datetime_taken = datetime_taken

            photo.save()


    @staticmethod
    def _update_information_from_video(video, video_file):
        if video.width is None or video.height is None or video.duration is None:
            information = get_information_from_video(video_file)

            video.width = information['width']
            video.height = information['height']
            video.duration = information['duration']
            video.datetime_taken = information['date_encoded']

            video.save()

    def resize_media(self):
        already_resized = None
        for size_type in self._sizes_type:
            qs = MediumResized.objects.values_list('medium', flat=True).filter(size_label=size_type).filter(medium__medium_type=self._medium_type)

            if already_resized is None:
                already_resized = qs
            else:
                already_resized |= qs
        media_to_be_resized = Medium.objects.filter(medium_type=self._medium_type).exclude(id__in=already_resized)

        verbose = self._medium_type == Medium.VIDEO

        if len(media_to_be_resized) == 0:
            print("Nothing to be resized? Aborting")
            sys.exit(1)

        if self._medium_type == Medium.PHOTO:
            total_steps = len(media_to_be_resized)
        else:
            total_steps = media_to_be_resized.aggregate(Sum('file_size'))['file_size__sum']

        progress_report = ProgressReport(total_steps, extra_information="Resizing medium to {}".format(",".join(self._sizes_type)),
                                         steps_are_bytes=self._medium_type == Medium.VIDEO)

        for medium in media_to_be_resized:
            if self._medium_type == Medium.PHOTO:
                progress_report.increment_and_print_if_needed()
            else:
                progress_report.increment_steps_and_print_if_needed(medium.file_size)

            # Download Media file from the bucket
            media_file = tempfile.NamedTemporaryFile(delete=False)
            media_file.close()
            start_download = time.time()
            self._media_bucket.bucket().download_file(medium.object_storage_key, media_file.name)
            download_time = time.time() - start_download

            assert os.stat(media_file.name).st_size == medium.file_size

            if verbose:
                speed = (medium.file_size / 1024 / 1024) / download_time        # MB/s
                print("Download Stats: Total size: {} Time: {} Speed: {:.2f} MB/s File: {}".format(utils.bytes_to_human_readable(medium.file_size),
                                                                                          utils.seconds_to_human_readable(download_time),
                                                                                          speed,
                                                                                          medium.object_storage_key))

            if medium.md5 is None:
                md5_media_file = utils.hash_of_file_path(media_file.name)
                medium.md5 = md5_media_file
                medium.save()

            self._resize_media(medium, media_file.name, self._sizes_type)

            print("Finished: medium.id: {}".format(medium.id))

            os.remove(media_file.name)

    def _resize_media(self, medium, media_file_name, sizes):
        for size_label in sizes:
            existing = MediumResized.objects.filter(medium=medium).filter(size_label=size_label)

            if len(existing) > 0:
                continue

            resized_medium = MediumResized()

            if size_label == 'O':
                resized_width = None
            else:
                resized_width = settings.IMAGE_LABEL_TO_SIZES[size_label][0]

            if medium.medium_type == Medium.PHOTO:
                self._update_information_from_photo_if_needed(medium, media_file_name)

                resized_medium_file = utils.resize_photo(media_file_name, resized_width)

                resized_image_information = Image.open(resized_medium_file)
                resized_medium.width = resized_image_information.width
                resized_medium.height = resized_image_information.height

            elif medium.medium_type == Medium.VIDEO:
                self._update_information_from_video(medium, media_file_name)

                assert size_label != "O" # Not supported to resize to the original size for videos

                start_time = time.time()
                resized_medium_file = utils.resize_video(media_file_name, resized_width)
                duration_convert = time.time() - start_time

                information = get_information_from_video(resized_medium_file)

                speed = information['duration'] / duration_convert

                print("Conversion took: {} Speed: {:.2f}x".format(utils.seconds_to_human_readable(duration_convert),
                                                                  speed))

                resized_medium.width = information['width']
                resized_medium.height = information['height']

            else:
                assert False

            md5_resized_file = utils.hash_of_file_path(resized_medium_file)
            _, resized_file_extension = os.path.splitext(resized_medium_file)
            resized_file_extension = resized_file_extension[1:].lower()

            # Upload medium to bucket
            resized_key = os.path.join(settings.RESIZED_PREFIX,
                                         md5_resized_file + "-{}.{}".format(size_label, resized_file_extension))

            resized_medium.object_storage_key = resized_key

            self._resizes_bucket.upload_file(resized_medium_file, resized_key)
            file_size = os.stat(resized_medium_file).st_size

            os.remove(resized_medium_file)

            # Update database
            resized_medium.md5 = md5_resized_file
            resized_medium.file_size = file_size
            resized_medium.size_label = size_label
            resized_medium.medium = medium
            resized_medium.datetime_resized = datetime.datetime.now(tz=timezone.utc)
            resized_medium.save()
