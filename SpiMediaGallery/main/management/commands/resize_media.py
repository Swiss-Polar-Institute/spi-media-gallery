from django.core.management.base import BaseCommand, CommandError

from main.models import Media, MediaResized
from django.conf import settings
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import datetime
import tempfile
import os
from pymediainfo import MediaInfo

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
            information['duration'] = track.duration / 1000

    return information


class Resizer(object):
    def __init__(self, bucket_name_media, bucket_name_thumbnails, size_type, media_type):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._thumbnails_bucket = spi_s3_utils.SpiS3Utils(bucket_name_thumbnails)
        self._size_type = size_type
        self._media_type = media_type

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
        already_resized = MediaResized.objects.values_list('media', flat=True).filter(size_label=self._size_type).filter(media__media_type=self._media_type)
        media_to_be_resized = Media.objects.filter(media_type=self._media_type).exclude(id__in=already_resized)

        progress_report = ProgressReport(len(media_to_be_resized), extra_information="Resizing media to {}".format(self._size_type))

        resized_width = None
        if self._size_type != 'O':
            resized_width = settings.IMAGE_LABEL_TO_SIZES[self._size_type][0]

        for media in media_to_be_resized:
            progress_report.increment_and_print_if_needed()

            # Read Media file
            media_object = self._media_bucket.get_object(media.object_storage_key)
            if media.object_storage_key is None or media.object_storage_key == "":
                continue

            media_file = tempfile.NamedTemporaryFile(delete=False)
            media_file.write(media_object.get()["Body"].read())
            media_file.close()

            assert os.stat(media_file.name).st_size == media.file_size

            if media.md5 is None:
                md5_media_file = utils.hash_of_file_path(media_file.name)
                media.md5 = md5_media_file

            resized_media = MediaResized()

            if media.media_type == Media.PHOTO:
                self.update_information_from_photo(media, media_file.name)

                thumbnail_file_name = utils.resize_photo(media_file.name, resized_width)

                resized_image_information = Image.open(thumbnail_file_name.name)
                resized_media.width = resized_image_information.width
                resized_media.height = resized_image_information.height

            elif media.media_type == Media.VIDEO:
                self.update_information_from_video(media, media_file.name)

                thumbnail_file_name = utils.resize_video(media_file.name, resized_width)

                information = get_information_from_video(thumbnail_file_name)

                resized_media.width = information['width']
                resized_media.height = information['height']

            else:
                assert False

            md5_resized_file = utils.hash_of_file_path(thumbnail_file_name)
            _, resized_file_extension = os.path.splitext(thumbnail_file_name)
            resized_file_extension = resized_file_extension[1:].lower()

            # Upload media to bucket
            thumbnail_key = os.path.join(settings.RESIZED_PREFIX, md5_resized_file + "-{}.{}".format(self._size_type, resized_file_extension))

            resized_media.object_storage_key = thumbnail_key

            self._thumbnails_bucket.upload_file(thumbnail_file_name, thumbnail_key)
            size = os.stat(thumbnail_file_name).st_size

            os.remove(thumbnail_file_name)
            os.remove(media_file.name)

            # Update database
            resized_media.md5 = md5_resized_file
            resized_media.file_size = size
            resized_media.size_label = self._size_type
            resized_media.media = media
            resized_media.save()
