from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, MediumResized, File
from django.conf import settings
import sys
import subprocess
from django.utils import timezone

import datetime
import tempfile
import os
import json
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

            else:
                information['date_encoded'] = None

    return information


def get_photo_information(image_filepath):
    command = ["exiftool", "-json", image_filepath]

    run = subprocess.run(command, stdout=subprocess.PIPE)
    output = run.stdout
    output = output.decode("utf-8")
    exif = json.loads(output)[0]

    image_information = {}
    image_information['width'] = exif['ImageWidth']
    image_information['height'] = exif['ImageHeight']

    if 'DateTimeOriginal' in exif:
        datetime_original = exif['DateTimeOriginal']

        # TODO: refactor this
        try:
            datetime_processed = datetime.datetime.strptime(datetime_original, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            try:
                datetime_processed = datetime.datetime.strptime(datetime_original, "%Y:%m:%d %H:%M:")
            except ValueError:
                datetime_processed = datetime.datetime.strptime(datetime_original, "%Y:%m:%d %H:%M")

        image_information['datetime_taken'] = datetime_processed

    return image_information


class Resizer(object):
    def __init__(self, bucket_name_media, bucket_name_resizes, sizes_type, medium_type):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._resizes_bucket = spi_s3_utils.SpiS3Utils(bucket_name_resizes)
        self._sizes_type = sizes_type
        self._medium_type = medium_type

    @staticmethod
    def _update_information_from_photo_if_needed(photo, photo_file):
        # Returns False if information should have been updated but it failed
        if photo.width is None or photo.height is None or photo.datetime_taken is None:
            photo_information = get_photo_information(photo_file)

            photo.width = photo_information["width"]
            photo.height = photo_information["height"]
            photo.datetime_taken = photo_information["datetime_taken"]

            photo.save()

    @staticmethod
    def _update_information_from_video(video, video_file):
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
            progress_report_unit = "photos"
        else:
            total_steps = media_to_be_resized.aggregate(Sum('file__size'))['file__size__sum']
            progress_report_unit = None

        progress_report = ProgressReport(total_steps, unit=progress_report_unit,
                                         extra_information="Resizing medium to {}".format(",".join(self._sizes_type)),
                                         steps_are_bytes=self._medium_type == Medium.VIDEO)

        for medium in media_to_be_resized:
            # Download Media file from the bucket
            suffix = utils.file_extension(medium.file.object_storage_key)
            media_file = tempfile.NamedTemporaryFile(suffix="." + suffix, delete=False)
            media_file.close()
            start_download = time.time()
            self._media_bucket.bucket().download_file(medium.file.object_storage_key, media_file.name)
            download_time = time.time() - start_download

            assert os.stat(media_file.name).st_size == medium.file.size

            if verbose:
                speed = (medium.file.size / 1024 / 1024) / download_time        # MB/s
                print("Download Stats. Size: {} Time: {} Speed: {:.2f} MB/s File: {}".format(utils.bytes_to_human_readable(medium.file.size),
                                                                                          utils.seconds_to_human_readable(download_time),
                                                                                          speed,
                                                                                          medium.file.object_storage_key))

            if medium.file.md5 is None:
                md5_media_file = utils.hash_of_file_path(media_file.name)
                medium.file.md5 = md5_media_file
                medium.file.save()

            self._resize_media(medium, media_file.name, self._sizes_type)

            print("Finished: medium.id: {}".format(medium.id))

            os.remove(media_file.name)

            if self._medium_type == Medium.PHOTO:
                progress_report.increment_and_print_if_needed()
            else:
                progress_report.increment_steps_and_print_if_needed(medium.file.size)

    def _resize_media(self, medium, medium_file_name, sizes):
        delete_file = None
        file_converted = False

        for size_label in sizes:
            existing = MediumResized.objects.filter(medium=medium).filter(size_label=size_label)

            if len(existing) > 0:
                continue

            if medium.file.size == 0:
                print("File {} size is 0, skipping".format(medium.file.object_storage_key))
                continue

            resized_medium = MediumResized()

            if size_label == 'O':
                resized_width = None
            else:
                resized_width = settings.IMAGE_LABEL_TO_SIZES[size_label][0]

            if medium.medium_type == Medium.PHOTO:
                self._update_information_from_photo_if_needed(medium, medium_file_name)

                if utils.file_extension(medium_file_name).lower() == "arw" and not file_converted:
                    temporary_intermediate_file = utils.convert_raw_to_ppm(medium_file_name)
                    file_converted = True
                    delete_file = temporary_intermediate_file
                    medium_file_name = temporary_intermediate_file

                resized_medium_file = utils.resize_photo(medium_file_name, resized_width)

                if os.stat(resized_medium_file).st_size == 0:
                    print("File {} resized output size is 0, skipping it".format(medium.file.object_storage_key))
                    continue

                resized_image_information = get_photo_information(resized_medium_file)
                resized_medium.width = resized_image_information['width']
                resized_medium.height = resized_image_information['height']

            elif medium.medium_type == Medium.VIDEO:
                self._update_information_from_video(medium, medium_file_name)

                assert size_label != "O" # Not supported to resize to the original size for videos

                start_time = time.time()
                resized_medium_file = utils.resize_video(medium_file_name, resized_width)

                if resized_medium_file is None:
                    print("File {} cannot be encoded".format(medium_file_name))
                    continue

                duration_convert = time.time() - start_time

                information = get_information_from_video(resized_medium_file)

                if 'duration' in information:
                    speed = information['duration'] / duration_convert

                    print("Conversion took: {} Speed: {:.2f}x".format(utils.seconds_to_human_readable(duration_convert),
                                                                    speed))
                else:
                    print("Conversion took: {} Speed: unknown, duration of video not known".format(utils.seconds_to_human_readable(duration_convert)))

                if 'width' in information and 'height' in information:
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

            self._resizes_bucket.upload_file(resized_medium_file, resized_key)
            file_size = os.stat(resized_medium_file).st_size

            os.remove(resized_medium_file)

            # Update database
            file = File()
            file.object_storage_key = resized_key
            file.md5 = md5_resized_file
            file.size = file_size
            file.save()

            resized_medium.file = file
            resized_medium.size_label = size_label
            resized_medium.medium = medium
            resized_medium.datetime_resized = datetime.datetime.now(tz=timezone.utc)
            resized_medium.save()

        if delete_file is not None:
            os.remove(delete_file)