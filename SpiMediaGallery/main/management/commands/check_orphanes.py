from django.conf import settings
from django.core.management.base import BaseCommand

from ... import spi_s3_utils
from ...models import Medium, MediumResized, File


class Command(BaseCommand):
    help = 'Finds files in the buckets not referenced by the database and files in the database that do not exist ' \
           'in the buckets. Check files for the recognized extensions only'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        check_orphanes = CheckOrphanes()
        check_orphanes.run()


class CheckOrphanes:
    def __init__(self):
        self._original_bucket = spi_s3_utils.SpiS3Utils('original')
        self._processed_bucket = spi_s3_utils.SpiS3Utils('processed')

    @staticmethod
    def _database_files(qs):
        file_keys = set()

        for row in qs:
            file_keys.add(row.file.object_storage_key)

        return file_keys

    @staticmethod
    def _database_media(qs):
        media_id = set()

        for row in qs:
            media_id.add(row.pk)

        return media_id

    @staticmethod
    def _file_ids_not_used():
        file_ids_medium = Medium.objects.values_list('file', flat=True)
        file_ids_mediumresized = MediumResized.objects.values_list('file', flat=True)
        all_file_ids = set(file_ids_medium).union(set(file_ids_mediumresized))

        unused_file_ids = File.objects.exclude(id__in=all_file_ids)

        return unused_file_ids

    def run(self):
        valid_extensions = settings.PHOTO_EXTENSIONS | settings.VIDEO_EXTENSIONS

        print('Collecting files from Media bucket')
        files_bucket_media = self._original_bucket.list_files('', only_from_extensions=valid_extensions)

        print('Collecting files from Media database')
        files_database_media = self._database_files(Medium.objects.all())

        print('Collecting files from Resized bucket')
        files_bucket_resized = self._processed_bucket.list_files(settings.RESIZED_PREFIX + '/',
                                                                 only_from_extensions=valid_extensions)

        print('Collecting files from Resized database')
        files_database_processed = self._database_files(MediumResized.objects.all())

        print('Calculating missing files')
        all_database_files = files_database_media.union(files_database_processed)
        all_bucket_files = files_bucket_media.union(files_bucket_resized)

        files_in_database_not_in_buckets = list(all_database_files - all_bucket_files)
        files_in_buckets_not_in_database = list(all_bucket_files - all_database_files)

        files_in_database_not_in_buckets.sort()
        files_in_buckets_not_in_database.sort()

        medium_without_files = self._database_media(Medium.objects.filter(file__isnull=True))

        print('Media without a file')
        for medium_pk in medium_without_files:
            print(medium_pk)

        print('Unused file IDs')
        for file in self._file_ids_not_used():
            print(file.id, file.object_storage_key)

        print('Files in the database missing in the buckets:')
        for file in files_in_database_not_in_buckets:
            print(file)

        print()
        print('Files in the buckets but not referenced in the database:')

        for file in files_in_buckets_not_in_database:
            print(file)
