from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, Tag
from libxmp.utils import file_to_dict
from django.core.exceptions import ObjectDoesNotExist

import os
import tempfile
import time

from main import spi_s3_utils
from main import utils


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('--prefix', type=str, default="", help="Prefix of the bucket to import files (e.g. a directory)")

    def handle(self, *args, **options):
        bucket_name = options["bucket_name"]
        prefix = options["prefix"]

        tagImporter = TagImporter(bucket_name, prefix)

        tagImporter.import_tags()


class TagImporter(object):
    def __init__(self, bucket_name, prefix):
        self._photo_bucket = spi_s3_utils.SpiS3Utils(bucket_name)
        self._prefix = prefix

    def import_tags(self):
        all_keys = self._photo_bucket.get_set_of_keys(self._prefix)

        non_xmp_without_xmp_associated = 0
        object_count = 0

        print("Total number of files to process:", len(all_keys))

        start_time = time.time()

        for s3_object in self._photo_bucket.objects_in_bucket(self._prefix):
            object_count += 1

            if object_count % 20 == 0:
                elapsed_time = time.time() - start_time
                speed = object_count / elapsed_time
                percentage = (object_count / len(all_keys)) * 100

                print("========== STATS")
                print("Processing {} of {}. Elapsed time: {:.2f} minutes Percentage: {:.2f}%".format(object_count,
                                                                                        len(all_keys),
                                                                                        elapsed_time / 60,
                                                                                        percentage))

                total_time = (len(all_keys) * elapsed_time) / object_count
                remaining_time = total_time - elapsed_time
                print("Photos per minute: {:.2f} Total remaining time: {:.2f} minutes".format(speed, remaining_time / 60))

            if s3_object.key.lower().endswith(".xmp"):
                continue

            size_of_media = s3_object.size

            xmp_file = s3_object.key + ".xmp"

            if xmp_file not in all_keys:
                # Non XMP file without an XMP associated
                non_xmp_without_xmp_associated += 1
                continue


            # Copies XMP into a file (libxmp seems to only be able to read
            # from physical files)
            xmp_object = self._photo_bucket.get_object(xmp_file)

            temporary_file = tempfile.NamedTemporaryFile(suffix=".xmp", delete=False)
            temporary_file.write(xmp_object.get()["Body"].read())
            temporary_file.close()

            # Extracts tags
            tags = self._extract_tags(temporary_file.name)

            # Inserts tags into the database
            if len(tags) > 0:
                try:
                    photo = Photo.objects.get(object_storage_key=s3_object.key)
                except ObjectDoesNotExist:
                    photo = Photo()
                    photo.object_storage_key = s3_object.key
                    photo.md5 = None
                    photo.file_size = size_of_media
                    photo.save()

                for tag in tags:
                    try:
                        tag_model = Tag.objects.get(tag=tag)
                    except ObjectDoesNotExist:
                        tag_model = Tag()
                        tag_model.tag = tag
                        tag_model.save()

                    photo.tags.add(tag_model)

            os.remove(temporary_file.name)

    @staticmethod
    def _extract_tags(file_path):
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
