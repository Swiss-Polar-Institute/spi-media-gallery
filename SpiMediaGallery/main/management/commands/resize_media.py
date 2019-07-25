from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, MediumResized
from django.conf import settings
from PIL import Image
import sys
Image.MAX_IMAGE_PIXELS = None

import datetime
import tempfile
import os
from pymediainfo import MediaInfo
from django.db.models import Sum

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_media', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('bucket_name_thumbnails', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('media_type', type=str, choices=["P", "V"], help="Resizes Photos or Videos")
        parser.add_argument('size_type', type=str, choices=["T", "S", "M", "L", "O"], help="Type of resizing (thumbnail, small, medium, large, original). Original changes the format to JPEG, potential rotation")

    def handle(self, *args, **options):
        bucket_name_media = options["bucket_name_media"]
        bucket_name_thumbnails = options["bucket_name_thumbnails"]
        media_type = options['media_type']
        size_type = options["size_type"]

        resizer = Resizer(bucket_name_media, bucket_name_thumbnails, size_type, media_type)

        resizer.resize_media()


def get_information_from_video(video_file):
    information = {}

    video_information = MediaInfo.parse(video_file)

    for track in video_information.tracks:
        if track.track_type == "Video":
            information['width'] = track.width
            information['height'] = track.height
            information['duration'] = float(track.duration) / 1000

    return information


class Resizer(object):
    def __init__(self, bucket_name_media, bucket_name_thumbnails, size_type, medium_type):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._thumbnails_bucket = spi_s3_utils.SpiS3Utils(bucket_name_thumbnails)
        self._size_type = size_type
        self._medium_type = medium_type

    @staticmethod
    def update_information_from_photo(photo, photo_file):
        if photo.width is None or photo.height is None or photo.datetime_taken is None:
            media_photo = Image.open(photo_file)
            photo.width = media_photo.width
            photo.height = media_photo.height

            exif_data = media_photo.getexif()

            EXIF_DATE_ID = 36867

            if EXIF_DATE_ID in exif_data:
                try:
                    datetime_taken = datetime.datetime.strptime(exif_data[EXIF_DATE_ID], "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    datetime_taken = None

                photo.datetime_taken = datetime_taken

            photo.save()


    @staticmethod
    def update_information_from_video(video, video_file):
        if video.width is None or video.height is None or video.duration is None:
            information = get_information_from_video(video_file)

            video.width = information['width']
            video.height = information['height']
            video.duration = information['duration']

            video.save()

    def resize_media(self):
        already_resized = MediumResized.objects.values_list('medium', flat=True).filter(size_label=self._size_type).filter(medium__medium_type=self._medium_type)
        media_to_be_resized = Medium.objects.filter(medium_type=self._medium_type).exclude(id__in=already_resized)

        if len(media_to_be_resized) == 0:
            print("Nothing to be resized? Aborting")
            sys.exit(1)

        if self._size_type == Medium.PHOTO:
            total_steps = len(media_to_be_resized)
        else:
            total_steps = media_to_be_resized.aggregate(Sum('file_size'))['file_size__sum']

        progress_report = ProgressReport(total_steps, extra_information="Resizing medium to {}".format(self._size_type))

        resized_width = None
        if self._size_type != 'O':
            resized_width = settings.IMAGE_LABEL_TO_SIZES[self._size_type][0]

        for medium in media_to_be_resized:
            if self._size_type == Medium.PHOTO:
                progress_report.increment_and_print_if_needed()
            else:
                progress_report.increment_steps_and_print_if_needed(medium.file_size)

            # Read Media file
            media_object = self._media_bucket.get_object(medium.object_storage_key)
            if medium.object_storage_key is None or medium.object_storage_key == "":
                continue

            media_file = tempfile.NamedTemporaryFile(delete=False)
            media_file.write(media_object.get()["Body"].read())
            media_file.close()

            assert os.stat(media_file.name).st_size == medium.file_size

            if medium.md5 is None:
                md5_media_file = utils.hash_of_file_path(media_file.name)
                medium.md5 = md5_media_file

            resized_medium = MediumResized()

            if medium.medium_type == Medium.PHOTO:
                self.update_information_from_photo(medium, media_file.name)

                thumbnail_file_name = utils.resize_photo(media_file.name, resized_width)

                resized_image_information = Image.open(thumbnail_file_name.name)
                resized_medium.width = resized_image_information.width
                resized_medium.height = resized_image_information.height

            elif medium.medium_type == Medium.VIDEO:
                self.update_information_from_video(medium, media_file.name)

                thumbnail_file_name = utils.resize_video(media_file.name, resized_width)

                information = get_information_from_video(thumbnail_file_name)

                resized_medium.width = information['width']
                resized_medium.height = information['height']

            else:
                assert False

            md5_resized_file = utils.hash_of_file_path(thumbnail_file_name)
            _, resized_file_extension = os.path.splitext(thumbnail_file_name)
            resized_file_extension = resized_file_extension[1:].lower()

            # Upload medium to bucket
            thumbnail_key = os.path.join(settings.RESIZED_PREFIX, md5_resized_file + "-{}.{}".format(self._size_type, resized_file_extension))

            resized_medium.object_storage_key = thumbnail_key

            self._thumbnails_bucket.upload_file(thumbnail_file_name, thumbnail_key)
            size = os.stat(thumbnail_file_name).st_size

            os.remove(thumbnail_file_name)
            os.remove(media_file.name)

            # Update database
            resized_medium.md5 = md5_resized_file
            resized_medium.file_size = size
            resized_medium.size_label = self._size_type
            resized_medium.medium = medium
            resized_medium.datetime_resized = datetime.datetime.now()
            resized_medium.save()
