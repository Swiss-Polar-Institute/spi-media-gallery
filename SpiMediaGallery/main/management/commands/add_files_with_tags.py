from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, Tag, File
from libxmp.utils import file_to_dict
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings

import os
import tempfile
import datetime
import time

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Updates photo tagging'

    def add_arguments(self, parser):
        parser.add_argument('--prefix', type=str, default="", help="Prefix of the bucket to import files (e.g. a directory)")

    def handle(self, *args, **options):
        bucket_name = "original"
        prefix = options["prefix"]

        tag_importer = TagImporter(bucket_name, prefix)

        tag_importer.import_tags()


class TagImporter(object):
    def __init__(self, bucket_name, prefix):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name)
        self._prefix = prefix

    def import_tags(self):
        all_keys = self._media_bucket.get_set_of_keys(self._prefix)

        non_xmp_without_xmp_associated = 0

        progress_report = ProgressReport(len(all_keys), extra_information="Adding files with tags")

        print("Total number of files to process:", len(all_keys))

        photo_extensions = settings.PHOTO_EXTENSIONS
        video_extensions = settings.VIDEO_EXTENSIONS

        valid_extensions = photo_extensions | video_extensions

        for s3_object in self._media_bucket.objects_in_bucket(self._prefix):
            progress_report.increment_and_print_if_needed()

            file_extension = utils.file_extension(s3_object.key).lower()

            if file_extension not in valid_extensions:
                continue

            size_of_medium = s3_object.size

            xmp_file = s3_object.key + ".xmp"

            tags = []
            temporary_tags_file = None

            if xmp_file in all_keys:
                # xmp_file exists in the list of files, it will download + extract tags

                # Copies XMP into a file (libxmp seems to only be able to read
                # from physical files)
                xmp_object = self._media_bucket.get_object(xmp_file)

                temporary_tags_file = tempfile.NamedTemporaryFile(suffix=".xmp", delete=False)
                temporary_tags_file.write(xmp_object.get()["Body"].read())
                temporary_tags_file.close()

                # Extracts tags
                tags = self._extract_tags(temporary_tags_file.name)

            else:
                # Non XMP file without an XMP associated
                non_xmp_without_xmp_associated += 1

            try:
                medium = Medium.objects.get(file__object_storage_key=s3_object.key)
            except ObjectDoesNotExist:
                medium = Medium()

                file = File()

                file.object_storage_key = s3_object.key
                file.md5 = None
                file.size = size_of_medium
                file.bucket = File.ORIGINAL
                file.save()

                medium.file = file

                if file_extension in photo_extensions:
                    medium.medium_type = Medium.PHOTO
                elif file_extension in video_extensions:
                    medium.medium_type = Medium.VIDEO
                else:
                    assert False

                medium.datetime_imported = datetime.datetime.now(tz=timezone.utc)
                medium.save()

            for tag in tags:
                try:
                    tag_model = Tag.objects.get(tag=tag)
                except ObjectDoesNotExist:
                    tag_model = Tag()
                    tag_model.tag = tag
                    tag_model.save()

                medium.tags.add(tag_model)

            if temporary_tags_file is not None:
                os.remove(temporary_tags_file.name)

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
