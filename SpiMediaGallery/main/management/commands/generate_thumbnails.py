from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, PhotoResized
from django.conf import settings
from PIL import Image

import tempfile
import os
import time

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport

class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_photos', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('bucket_name_thumbnails', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")

    def handle(self, *args, **options):
        bucket_name_photos = options["bucket_name_photos"]
        bucket_name_thumbnails = options["bucket_name_thumbnails"]

        thumbnail_generator = ThumbnailGenerator(bucket_name_photos, bucket_name_thumbnails)

        thumbnail_generator.resize_images(415)


class ThumbnailGenerator(object):
    def __init__(self, bucket_name_photos, bucket_name_thumbnails):
        self._photo_bucket = spi_s3_utils.SpiS3Utils(bucket_name_photos)
        self._thumbnails_bucket = spi_s3_utils.SpiS3Utils(bucket_name_thumbnails)

    def resize_images(self, resized_width):
        count = 0

        thumbnails = PhotoResized.objects.values_list('photo', flat=True).filter(size_label="T")
        photos_without_thumbnail = Photo.objects.all().exclude(id__in=thumbnails)
        # photos_without_thumbnail = Photo.objects.filter(thumbnail__isnull=True)

        progress_report = ProgressReport(len(photos_without_thumbnail))

        for photo in photos_without_thumbnail:
            progress_report.increment_and_print_if_needed()

            # Read Photo
            photo_object = self._photo_bucket.get_object(photo.object_storage_key)
            if photo.object_storage_key is None or photo.object_storage_key == "":
                continue

            # print("Processing thumbnail {} of {}".format(count, photos_without_thumbnail_count))

            photo_file = tempfile.NamedTemporaryFile(delete=False)
            photo_file.write(photo_object.get()["Body"].read())
            photo_file.close()

            assert os.stat(photo_file.name).st_size == photo.file_size

            md5_photo_file = utils.hash_of_fp(photo_file.name)


            thumbnail_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            thumbnail_file.close()

            # Resize photo
            utils.resize_file(photo_file.name, thumbnail_file.name, resized_width)

            # Upload photo to bucket
            thumbnail_key = os.path.join(settings.RESIZED_PREFIX, md5_photo_file + "-{}.jpg".format(resized_width))

            self._thumbnails_bucket.upload_file(thumbnail_file.name, thumbnail_key)
            md5_resized_file = utils.hash_of_fp(thumbnail_file.name)
            size = os.stat(thumbnail_file.name).st_size

            thumbnail_image = Image.open(thumbnail_file.name)
            thumbnail_width = thumbnail_image.width
            thumbnail_height = thumbnail_image.height

            os.remove(thumbnail_file.name)

            # Update database
            thumbnail = PhotoResized()
            thumbnail.object_storage_key = thumbnail_key
            thumbnail.width = thumbnail_width
            thumbnail.height = thumbnail_height
            thumbnail.md5 = md5_resized_file
            thumbnail.file_size = size
            thumbnail.size_label = "T"
            thumbnail.photo = photo
            thumbnail.save()

            print("Size:", size)

            photo.thumbnail = thumbnail
            photo.save()