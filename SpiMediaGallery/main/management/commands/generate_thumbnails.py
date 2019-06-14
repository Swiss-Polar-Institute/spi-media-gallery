from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, Thumbnail
from django.conf import settings

from PIL import Image
from resizeimage import resizeimage
import boto3
import tempfile

import sys


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_photos', type=str, help="Bucket name - it needs to exist in settings.py in MEDIA_BUCKETS")
        parser.add_argument('bucket_name_thumbnails', type=str, help="Bucket name - it needs to exist in settings.py in MEDIA_BUCKETS")

    def handle(self, *args, **options):
        bucket_name_photos = options["bucket_name_photos"]
        bucket_name_thumbnails = options["bucket_name_thumbnails"]

        thumbnailGenerator = ThumbnailGenerator(bucket_name_photos, bucket_name_thumbnails)

        thumbnailGenerator.generate_thumbnails()


class ThumbnailGenerator(object):
    def __init__(self, bucket_name_photos, bucket_name_thumbnails):
        buckets = settings.MEDIA_BUCKETS

        if bucket_name_photos not in buckets:
            print("Bucket name is '{}'. Possible bucket names: {}".format(bucket_name_photos, ", ".join(buckets.keys())), file=sys.stderr)
            sys.exit(1)

        if bucket_name_thumbnails not in buckets:
            print("Bucket name is '{}'. Possible bucket names: {}".format(bucket_name_thumbnails, ", ".join(buckets.keys())), file=sys.stderr)
            sys.exit(1)

        self._bucket_photos_configuration = buckets[bucket_name_photos]
        self._bucket_thumbnails_configuration = buckets[bucket_name_thumbnails]

    def _get_keys_from_bucket(self, bucket):
        keys = set()
        for o in self._get_objects_in_bucket(bucket):
            keys.add(o.key)

        return keys

    def _get_objects_in_bucket(self, bucket):
        s3_objects = self._connect_to_bucket(bucket).objects.filter(Prefix=self._prefix).all()

        return s3_objects

    def _connect_to_s3(self, bucket):
        return boto3.resource(service_name="s3",
                            aws_access_key_id=bucket['access_key'],
                            aws_secret_access_key=bucket['secret_key'],
                            endpoint_url=bucket['endpoint'])

    def _connect_to_bucket(self, bucket):
        bucket = self._connect_to_s3(bucket).Bucket(bucket['name'])

        return bucket

    def generate_thumbnails(self):
        for photo in Photo.objects.filter(thumbnail__isnull=True):
            # Read Photo
            photo_object = self._connect_to_s3(self._bucket_photos_configuration).Object(self._bucket_photos_configuration["name"], photo.object_storage_key)

            photo_file = tempfile.NamedTemporaryFile()
            photo_file.write(photo_object.get()["Body"].read())
            photo_file.seek(0)

            # Resize photo
            image = Image.open(photo_file)
            resized = resizeimage.resize_width(image, 415)

            thumbnail_file = tempfile.NamedTemporaryFile(prefix=photo.md5, delete=False)
            thumbnail_file.close()

            resized.save(thumbnail_file.name, "JPEG")

            # Upload photo to bucket
            thumbnail_bucket = self._connect_to_s3(self._bucket_thumbnails_configuration)

            thumbnail_object_storage_key = photo.md5 + "-thumbnail.jpg"

            thumbnail_bucket.meta.client.upload_file(thumbnail_file.name, self._bucket_thumbnails_configuration['name'], photo.md5 + "-thumbnail.jpg")

            # Update database
            thumbnail = Thumbnail()
            thumbnail.object_storage_key = thumbnail_object_storage_key
            thumbnail.width = 415
            thumbnail.height = 100
            thumbnail.md5 = "cccc"
            thumbnail.save()

            photo.thumbnail = thumbnail
            photo.save()