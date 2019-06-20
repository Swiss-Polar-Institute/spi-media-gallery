from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, PhotoResized
from django.conf import settings
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import datetime
import tempfile
import os

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_photos', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('bucket_name_thumbnails', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('size_type', type=str, choices=["T", "S", "M", "L", "O"], help="Type of resizing (thumbnail, small, medium, large, original). Original changes the format to JPEG, potential rotation")

    def handle(self, *args, **options):
        bucket_name_photos = options["bucket_name_photos"]
        bucket_name_thumbnails = options["bucket_name_thumbnails"]
        size_type = options["size_type"]

        resizer = Resizer(bucket_name_photos, bucket_name_thumbnails, size_type)

        resizer.resize_images()


class Resizer(object):
    def __init__(self, bucket_name_photos, bucket_name_thumbnails, size_type):
        self._photo_bucket = spi_s3_utils.SpiS3Utils(bucket_name_photos)
        self._thumbnails_bucket = spi_s3_utils.SpiS3Utils(bucket_name_thumbnails)
        self._size_type = size_type

    def resize_images(self):
        already_resized = PhotoResized.objects.values_list('photo', flat=True).filter(size_label=self._size_type)
        photos_to_be_resized = Photo.objects.all().exclude(id__in=already_resized)

        progress_report = ProgressReport(len(photos_to_be_resized), "Resizing photos to {}".format(self._size_type))

        resized_width = None
        if self._size_type != 'O':
            resized_width = settings.IMAGE_LABEL_TO_SIZES[self._size_type][0]

        for photo in photos_to_be_resized:
            progress_report.increment_and_print_if_needed()

            # Read Photo
            photo_object = self._photo_bucket.get_object(photo.object_storage_key)
            if photo.object_storage_key is None or photo.object_storage_key == "":
                continue

            photo_file = tempfile.NamedTemporaryFile(delete=False)
            photo_file.write(photo_object.get()["Body"].read())
            photo_file.close()

            assert os.stat(photo_file.name).st_size == photo.file_size

            if photo.md5 is None:
                md5_photo_file = utils.hash_of_file_path(photo_file.name)
                photo.md5 = md5_photo_file

            if photo.width is None or photo.height is None or photo.datetime_taken is None:
                photo_image = Image.open(photo_file.name)
                photo.width = photo_image.width
                photo.height = photo_image.height

                exif_data = photo_image.getexif()

                EXIF_DATE_ID = 36867

                if EXIF_DATE_ID in exif_data:
                    try:
                        datetime_taken = datetime.datetime.strptime(exif_data[EXIF_DATE_ID], "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        datetime_taken = None

                    photo.datetime_taken = datetime_taken

            photo.save()

            thumbnail_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            thumbnail_file.close()

            # Resize photo
            utils.resize_file(photo_file.name, thumbnail_file.name, resized_width)
            md5_resized_file = utils.hash_of_file_path(thumbnail_file.name)

            # Upload photo to bucket
            thumbnail_key = os.path.join(settings.RESIZED_PREFIX, md5_resized_file + "-{}.jpg".format(self._size_type))

            self._thumbnails_bucket.upload_file(thumbnail_file.name, thumbnail_key)
            size = os.stat(thumbnail_file.name).st_size

            thumbnail_image = Image.open(thumbnail_file.name)
            thumbnail_width = thumbnail_image.width
            thumbnail_height = thumbnail_image.height

            os.remove(thumbnail_file.name)
            os.remove(photo_file.name)

            # Update database
            resized_photo = PhotoResized()
            resized_photo.object_storage_key = thumbnail_key
            resized_photo.width = thumbnail_width
            resized_photo.height = thumbnail_height
            resized_photo.md5 = md5_resized_file
            resized_photo.file_size = size
            resized_photo.size_label = self._size_type
            resized_photo.photo = photo
            resized_photo.save()
