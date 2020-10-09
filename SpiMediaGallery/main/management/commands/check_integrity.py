from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import BaseCommand

from ... import spi_s3_utils
from ...models import Medium, MediumResized, File, Tag, TagName

from ... import utils

from typing import Dict, Optional


class Command(BaseCommand):
    help = 'Check integrity: unused tags, unused files in the object storage, files used in the DB' \
           'but does not exist in the object storage, etc.'

    def add_arguments(self, parser):
        parser.add_argument('elements', type=str, choices=['files', 'tags', 'xmp_files', 'everything'],
                            help='')

        parser.add_argument('--bucket', type=str, choices=['original', 'processed', 'imported'],
                            help='Does the file checks only the specified bucket. If not specified: all the buckets')

    def handle(self, *args, **options):
        bucket = options['bucket']
        elements = options['elements']

        to_test = []
        if elements == 'everything':
            to_test = ['files', 'tags', 'xmp_files']
        elif elements == 'files':
            to_test = ['files']
        elif elements == 'tags':
            to_test = ['tags']
        elif elements == 'xmp_files':
            to_test = ['xmp_files']

        check_orphanes = CheckOrphanes(to_test, bucket)
        check_orphanes.run()


class CheckOrphanes:
    def __init__(self, elements, bucket_to_check):
        self._elements = elements
        self._bucket_to_check = bucket_to_check

        self._bucket_utils = {'original': spi_s3_utils.SpiS3Utils('original'),
                              'processed': spi_s3_utils.SpiS3Utils('processed')
                              }

        # This is a cache of the files in the bucket (since it can be needed multiple times).
        # The first dictionary is the bucket. The second dictionary's key is the
        # file extensions that we've requested. Some of the code only needs media file extensions,
        # some all. It keeps a cache for each one and resuses appropiately
        self._files_in_bucket: Dict[str, Dict[frozenset, set]] = {'original': {},
                                                                  'processed': {}
                                                                  }

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
        if 'files' in self._elements:
            self.check_orphaned_files()

        if 'tags' in self._elements:
            self.check_orphaned_tags()

        if 'xmp_files' in self._elements:
            self.check_xmp_files()

    def check_xmp_files(self):
        xmps_without_medium = 0
        media_without_xmp = 0
        media_count = 0
        xmps_count = 0
        xmps_without_medium_list = []

        recognised_file_extensions = settings.PHOTO_FORMATS.keys() | settings.VIDEO_FORMATS.keys()
        all_keys = self._get_files_in_bucket('original')

        for key in all_keys:
            if key.endswith('.xmp'):
                xmps_count += 1

                medium_file = key[0:-(len('.xmp'))]

                medium_file_extension = utils.file_extension(medium_file).lower()

                if medium_file_extension in recognised_file_extensions and medium_file not in all_keys:
                    xmps_without_medium += 1
                    xmps_without_medium_list.append(key)

            if utils.file_extension(key).lower() in recognised_file_extensions:
                media_count += 1
                xmp_file = key + '.xmp'

                if xmp_file not in all_keys:
                    media_without_xmp += 1

        print('* Total XMP files:', xmps_count)
        print('* Total Medium files:', media_count)
        print('* XMPs without a Medium:', xmps_without_medium)
        print('* Media without an XMP:', media_without_xmp)

        print('* XMP files for a recognized extension that does not have a Medium file:')
        if len(xmps_without_medium_list) > 0:
            xmps_without_medium_list.sort()

            for file in xmps_without_medium_list:
                print('  ' + file)

    def _get_files_in_bucket(self, bucket_name, extensions_filter=frozenset()):
        extensions_filter = frozenset(extensions_filter)
        if self._files_in_bucket[bucket_name] is None or extensions_filter not in self._files_in_bucket[bucket_name]:
            print('Collecting files from {} extension filter {}...'.format(bucket_name, extensions_filter))
            if extensions_filter == frozenset():
                extensions_filter_or_none = None
            else:
                extensions_filter_or_none = extensions_filter

            self._files_in_bucket[bucket_name][extensions_filter] = self._bucket_utils[bucket_name].list_files('',
                                                                                                               only_from_extensions=extensions_filter_or_none)
            print('Number of files collected: {}'.format(len(self._files_in_bucket[bucket_name][extensions_filter])))

        return self._files_in_bucket[bucket_name][extensions_filter]

    def check_orphaned_files(self):
        files_bucket_original = set()
        files_database_original = set()
        files_bucket_processed = set()
        files_database_processed = set()

        valid_media_extensions = settings.PHOTO_FORMATS.keys() | settings.VIDEO_FORMATS.keys()

        if self._bucket_to_check is None or self._bucket_to_check == 'original':
            files_bucket_original = self._get_files_in_bucket('original', valid_media_extensions)

            print('Collecting files from original database...')
            files_database_original = self._database_files(Medium.objects.all())

        if self._bucket_to_check is None or self._bucket_to_check == 'processed':
            files_bucket_processed = self._get_files_in_bucket('processed', valid_media_extensions)

            print('Collecting files from Resized database...')
            files_database_processed = self._database_files(MediumResized.objects.all())

        print('Calculating missing files...')
        all_database_files = files_database_original.union(files_database_processed)
        all_bucket_files = files_bucket_original.union(files_bucket_processed)

        files_in_database_not_in_buckets = list(all_database_files - all_bucket_files)
        files_in_buckets_not_in_database = list(all_bucket_files - all_database_files)

        files_in_database_not_in_buckets.sort()
        files_in_buckets_not_in_database.sort()

        medium_without_files = self._database_media(Medium.objects.filter(file__isnull=True))

        print('* Media without a file')
        for medium_pk in medium_without_files:
            print(medium_pk)
        print()

        print('* Unused file IDs')
        for file in self._file_ids_not_used():
            print(file.id, file.object_storage_key)
        print()

        print('* Files in the database missing in the buckets:')
        for file in files_in_database_not_in_buckets:
            print(file)

        print()
        print('* Files in the buckets but not referenced in the database:')

        for file in files_in_buckets_not_in_database:
            print(file)
        print()

    def check_orphaned_tags(self):
        print('* TagNames not referenced by any Tag:')

        for tag_name in TagName.objects.all():
            try:
                Tag.objects.get(name=tag_name)
            except ObjectDoesNotExist:
                print('TagName: {} not used by any Tag'.format(tag_name.name))
            except MultipleObjectsReturned:
                pass
        print()

        print('* Tags not referenced by any Medium:')
        for tag in Tag.objects.all():
            try:
                Medium.objects.get(tags=tag)
            except ObjectDoesNotExist:
                print('Tag: {} not used by any Medium'.format(tag_name))
            except MultipleObjectsReturned:
                pass
        print()
