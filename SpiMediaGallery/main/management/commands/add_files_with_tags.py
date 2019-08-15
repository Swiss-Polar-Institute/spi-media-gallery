from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, Tag, TagName, File
from libxmp.utils import file_to_dict
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings

import os
import tempfile
import datetime

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport
from .generate_virtual_tags import generate_virtual_tags
from typing import Optional, Set
from django.db import transaction


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
    def __init__(self, bucket_name: str, prefix: str):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name)
        self._prefix = prefix
        self.all_keys: Optional[Set[str]] = None
        self.valid_extensions = settings.PHOTO_EXTENSIONS | settings.VIDEO_EXTENSIONS

    def import_tags(self):
        self.all_keys = self._media_bucket.get_set_of_keys(self._prefix)

        progress_report = ProgressReport(len(self.all_keys), extra_information="Adding files with tags")

        print("Total number of files to process:", len(self.all_keys))

        for s3_object in self._media_bucket.objects_in_bucket(self._prefix):
            progress_report.increment_and_print_if_needed()

            self._process_s3_object(s3_object)

    @transaction.atomic
    def _process_s3_object(self, s3_object):
        file_extension = utils.file_extension(s3_object.key).lower()

        if file_extension not in self.valid_extensions:
            return

        size_of_medium = s3_object.size

        xmp_file = s3_object.key + ".xmp"

        tags = []

        temporary_tags_file = None

        if xmp_file in self.all_keys:
            # xmp_file exists in the list of files, it will download + extract tags

            # Copies XMP into a file (libxmp seems to only be able to read
            # from physical files)
            xmp_object = self._media_bucket.get_object(xmp_file)

            temporary_tags_file = tempfile.NamedTemporaryFile(suffix=".xmp", delete=False)
            temporary_tags_file.write(xmp_object.get()["Body"].read())
            temporary_tags_file.close()

            # Extracts tags
            tags = self._extract_tags(temporary_tags_file.name)

        medium: Medium

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

            if file_extension in settings.PHOTO_EXTENSIONS:
                medium.medium_type = Medium.PHOTO
            elif file_extension in settings.VIDEO_EXTENSIONS:
                medium.medium_type = Medium.VIDEO
            else:
                assert False

            medium.datetime_imported = datetime.datetime.now(tz=timezone.utc)
            medium.save()

        # Delete existing tags of the Medium to import it again
        medium.tags.clear()

        for tag in tags:
            try:
                tag_name = TagName.objects.get(name=tag)
            except ObjectDoesNotExist:
                tag_name = TagName()
                tag_name.name = tag
                tag_name.save()

            try:
                tag = Tag.objects.get(name=tag_name, importer=Tag.XMP)
            except ObjectDoesNotExist:
                tag = Tag(name=tag_name, importer=Tag.XMP)
                tag.save()

            medium.tags.add(tag)

        generate_virtual_tags(medium)

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
