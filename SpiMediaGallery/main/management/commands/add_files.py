from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, Tag
from django.conf import settings
from libxmp.utils import file_to_dict
from django.core.exceptions import ObjectDoesNotExist
import os
import boto3
import sys
import tempfile
import hashlib


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name', type=str, help="Bucket name - it needs to exist in settings.py in MEDIA_BUCKETS")
        parser.add_argument('--prefix', type=str, default="", help="Prefix of the bucket to import files (e.g. a directory)")

    def handle(self, *args, **options):
        bucket_name = options["bucket_name"]
        prefix = options["prefix"]

        tagImporter = TagImporter(bucket_name, prefix)

        tagImporter.import_tags()


class TagImporter(object):
    def __init__(self, bucket_name, prefix):
        buckets = settings.MEDIA_BUCKETS

        if bucket_name not in buckets:
            print("Bucket name is '{}'. Possible bucket names: {}".format(bucket_name, ", ".join(buckets.keys())), file=sys.stderr)
            sys.exit(1)

        self._prefix = prefix

        self._bucket_configuration = buckets[bucket_name]

    def _get_keys_from_bucket(self):
        keys = set()
        for o in self._get_objects_in_bucket():
            keys.add(o.key)

        return keys

    def _get_objects_in_bucket(self):
        s3_objects = self._connect_to_bucket().objects.filter(Prefix=self._prefix).all()

        return s3_objects

    def _connect_to_s3(self):
        return boto3.resource(service_name="s3",
                            aws_access_key_id=self._bucket_configuration['access_key'],
                            aws_secret_access_key=self._bucket_configuration['secret_key'],
                            endpoint_url=self._bucket_configuration['endpoint'])

    def _connect_to_bucket(self):
        bucket = self._connect_to_s3().Bucket(self._bucket_configuration['name'])

        return bucket

    def import_tags(self):
        keys_set = self._get_keys_from_bucket()

        non_xmp_without_xmp_associated = 0
        object_count = 0

        for s3_object in self._get_objects_in_bucket():
            object_count += 1

            if s3_object.key.lower().endswith(".xmp"):
                continue

            base, extension = os.path.splitext(s3_object.key)
            xmp_file = s3_object.key + ".xmp"

            if xmp_file not in keys_set:
                # Non XMP file without an XMP associated
                non_xmp_without_xmp_associated += 1
                continue


            # Hash of the media file
            h = hashlib.md5()
            for chunk in s3_object.get()["Body"].iter_chunks(100*1024*1024):
                h.update(chunk)
            md5 = h.hexdigest()

            # Copies XMP into a file (libxmp seems to only be able to read
            # from physical files)
            xmp_object = self._connect_to_s3().Object(self._bucket_configuration["name"], xmp_file)
            print(xmp_object)

            temporary_file = tempfile.NamedTemporaryFile()
            temporary_file.write(xmp_object.get()["Body"].read())
            temporary_file.seek(0)

            # Extracts tags
            tags = self.extract_tags(temporary_file.name)

            print(s3_object.key)
            print(temporary_file.name)
            print(tags)
            print(md5)
            print("-----------")

            # Inserts tags into the database
            if len(tags) > 0:
                try:
                    photo = Photo.objects.get(key=temporary_file)
                except ObjectDoesNotExist:
                    photo = Photo()
                    photo.key = s3_object.key
                    photo.md5 = md5
                    photo.save()

                for tag in tags:
                    try:
                        tag_model = Tag.objects.get(tag=tag)
                    except ObjectDoesNotExist:
                        tag_model = Tag()
                        tag_model.tag = tag
                        tag_model.save()

                    photo.tags.add(tag_model)


    def extract_tags(self, file_path):
        tags = set()

        xmp = file_to_dict(file_path)

        if "http://www.digikam.org/ns/1.0/" in xmp:
            for tag_section in xmp['http://www.digikam.org/ns/1.0/']:
                if len(tag_section) == 0:
                    continue

                tag = tag_section[1]
                if tag != "":
                    tags.add(tag)

        return tags