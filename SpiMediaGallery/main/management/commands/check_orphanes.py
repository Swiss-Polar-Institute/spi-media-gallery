from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, MediumResized
from django.conf import settings

from main import spi_s3_utils

import time
from main import utils

class Command(BaseCommand):
    help = 'Finds orphaned files'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_media', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")
        parser.add_argument('bucket_name_resized', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")

    def handle(self, *args, **options):
        bucket_name_media = options["bucket_name_media"]
        bucket_name_resized = options["bucket_name_resized"]

        check_orphanes = CheckOrphanes(bucket_name_media, bucket_name_resized)

        check_orphanes.run()


class CheckOrphanes(object):
    def __init__(self, bucket_name_media, bucket_name_resizes):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)
        self._resizes_bucket = spi_s3_utils.SpiS3Utils(bucket_name_resizes)

    def _database_files(self, qs):
        s = set()

        for file in qs:
            s.add(file.object_storage_key)

        return s

    def run(self):
        valid_extensions = settings.PHOTO_EXTENSIONS | settings.VIDEO_EXTENSIONS

        files_bucket_media = self._media_bucket.list_files("", only_from_extensions=valid_extensions)
        files_database_media = self._database_files(Medium.objects.all())

        files_bucket_resized = self._resizes_bucket.list_files(settings.RESIZED_PREFIX + "/", only_from_extensions=valid_extensions)
        files_database_resized = self._database_files(MediumResized.objects.all())

        all_database_files = files_database_media.union(files_database_resized)
        all_bucket_files = files_bucket_media.union(files_bucket_resized)

        print("Files in the database missing in the buckets")

        for file in all_database_files - all_bucket_files:
            print(file)

        print("Files in the buckets but not referenced in the database, without XMP")
        files_in_buckets_not_in_database = all_bucket_files - all_database_files

        for file in files_in_buckets_not_in_database:
            print(file)