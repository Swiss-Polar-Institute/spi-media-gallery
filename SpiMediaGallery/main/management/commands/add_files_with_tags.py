import datetime
import os
import tempfile
from typing import Optional, Set

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import transaction, OperationalError
from django.utils import timezone

from .generate_virtual_tags import generate_virtual_tags
from ... import spi_s3_utils
from ... import utils
from ...models import Medium, Tag, TagName, File
from ...progress_report import ProgressReport
from ...xmp_utils import XmpUtils


class Command(BaseCommand):
    help = 'From the "original" bucket: list the files (photos or videos), adds them into the database (only the name ' \
           ' and file size since it is not downloading the files. It downloads the associated .xmp file and attach ' \
           'the  digiKam tags into the medium. Note that it generates virtual tags: e.g. if a tag is ' \
           '"people/john_doe" it will also add "people" '

    def add_arguments(self, parser):
        parser.add_argument('--prefix', type=str, default='',
                            help='Prefix of the files to be imported.')

    def handle(self, *args, **options):
        bucket_name = 'original'
        prefix = options['prefix']

        media_importer = MediaImporter(bucket_name, prefix)

        media_importer.import_media()


class MediaImporter(object):
    def __init__(self, bucket_name: str, prefix: str):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name)
        self._prefix = prefix
        self._all_keys: Optional[Set[str]] = None
        self._valid_extensions = settings.PHOTO_FORMATS.keys() | settings.VIDEO_FORMATS.keys()

    def import_media(self):
        self._all_keys = self._media_bucket.get_set_of_keys(self._prefix)

        progress_report = ProgressReport(len(self._all_keys), extra_information='Adding files with tags')

        for s3_object in self._media_bucket.objects_in_bucket(self._prefix):
            progress_report.increment_and_print_if_needed()

            self._process_s3_object(s3_object)

    @transaction.atomic
    def _process_s3_object(self, s3_object):
        file_extension = utils.file_extension(s3_object.key).lower()

        if file_extension not in self._valid_extensions:
            return

        size_of_medium = s3_object.size

        xmp_file = s3_object.key + '.xmp'

        tags = self._download_xmp_read_tags(xmp_file)
        medium = self._create_or_found_medium(s3_object.key, size_of_medium)
        self._set_tags(medium, tags)
        generate_virtual_tags(medium)

    def _download_xmp_read_tags(self, xmp_key):
        tags = {}

        if xmp_key in self._all_keys:
            # xmp_file exists in the list of files, it will download + extract tags

            # Copies XMP into a file (libxmp seems to only be able to read
            # from physical files)
            xmp_object = self._media_bucket.get_object(xmp_key)

            temporary_tags_file = tempfile.NamedTemporaryFile(suffix='.xmp', delete=False)
            temporary_tags_file.write(xmp_object.get()['Body'].read())
            temporary_tags_file.close()

            # Extracts tags
            tags = XmpUtils.read_tags(temporary_tags_file.name)

            os.unlink(temporary_tags_file.name)

        return tags

    @staticmethod
    def _create_or_found_medium(s3_object_key, size_of_medium):
        medium: Medium

        try:
            medium = Medium.objects.get(file__object_storage_key=s3_object_key)
            assert medium.file

        except ObjectDoesNotExist:
            file_extension = utils.file_extension(s3_object_key).lower()
            medium = Medium()

            file = File()

            file.object_storage_key = s3_object_key
            file.md5 = None
            file.size = size_of_medium
            file.bucket = File.ORIGINAL
            file.save()

            medium.file = file

            if file_extension in settings.PHOTO_FORMATS:
                medium.medium_type = Medium.PHOTO
            elif file_extension in settings.VIDEO_FORMATS:
                medium.medium_type = Medium.VIDEO
            else:
                assert False

            medium.datetime_imported = datetime.datetime.now(tz=timezone.utc)
            medium.save()

        except OperationalError as error:
            print("Failed: ", s3_object_key)
            raise error

        return medium

    @staticmethod
    def _set_tags(medium, tags):
        # Delete existing tags of the Medium to import it again
        medium.tags.clear()

        for tag in tags:
            # Find or create the tag_name
            try:
                tag_name = TagName.objects.get(name=tag)
            except ObjectDoesNotExist:
                tag_name = TagName()
                tag_name.name = tag
                tag_name.save()

            # Find or create the tag_name tag with XMP
            try:
                tag = Tag.objects.get(name=tag_name, importer=Tag.XMP)
            except ObjectDoesNotExist:
                tag = Tag(name=tag_name, importer=Tag.XMP)
                tag.save()

            medium.tags.add(tag)
