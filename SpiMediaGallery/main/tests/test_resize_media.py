import os

from django.conf import settings
from django.test import TestCase
from moto import mock_s3

from ..management.commands.add_files_with_tags import MediaImporter
from ..management.commands.resize_media import Resizer
from ..models import *


# All the Boto S3 calls are mocked


class ResizeMediaTest(TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(ResizeMediaTest, self).__init__(*args, **kwargs)

        # mock_s3 only works with the default endpoint
        settings.BUCKETS_CONFIGURATION['original']['endpoint'] = None
        settings.BUCKETS_CONFIGURATION['processed']['endpoint'] = None

    @classmethod
    def setUpClass(cls):
        super(ResizeMediaTest, cls).setUpClass()

    def setUp(self):
        self._mock = mock_s3()
        self._mock.start()

        self._spi_s3_utils_original = SpiS3Utils('original')
        spi_s3_utils_resource_original = self._spi_s3_utils_original.resource()
        spi_s3_utils_resource_original.create_bucket(Bucket='spi-media-gallery-original')

        self._spi_s3_utils_processed = SpiS3Utils('processed')
        spi_s3_utils_resource_processed = self._spi_s3_utils_processed.resource()
        spi_s3_utils_resource_processed.create_bucket(Bucket='spi-media-gallery-processed')

        MediumResized.objects.all().delete()
        Medium.objects.all().delete()

    def tearDown(self):
        pass

    def _upload_fixture_files(self) -> None:
        fixtures_buckets_original_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                           '../fixtures/buckets/original')

        for root, dirs, files in os.walk(fixtures_buckets_original_directory):
            for file in files:
                full_path_file = os.path.join(root, file)
                relative_directory_for_object_storage = root[len(fixtures_buckets_original_directory) + 1:]
                key = os.path.join(relative_directory_for_object_storage, file)

                self._spi_s3_utils_original.upload_file(full_path_file, key)

    def test_resize_photos(self):
        self._upload_fixture_files()
        tag_import = MediaImporter('original', '')
        tag_import.import_media()

        self.assertEqual(MediumResized.objects.count(), 0)
        self.assertEqual(len(self._spi_s3_utils_processed.list_files('')), 0)

        resizer = Resizer('processed', ['T', 'S', 'L'], 'Photos')
        resizer.resize_media()

        self.assertEqual(MediumResized.objects.count(), 3)
        self.assertEqual(len(self._spi_s3_utils_processed.list_files('')), 3)

        medium = Medium.objects.filter(medium_type=Medium.PHOTO)[0]

        thumbnail = MediumResized.objects.get(medium=medium, size_label="T")
        self.assertEqual(thumbnail.width, 415)
        self.assertEqual(thumbnail.height, 311)

        small = MediumResized.objects.get(medium=medium, size_label="S")
        self.assertEqual(small.width, 640)
        self.assertEqual(small.height, 480)

        large = MediumResized.objects.get(medium=medium, size_label="L")
        self.assertEqual(large.width, 1920)
        self.assertEqual(large.height, 1440)

    def test_resize_videos(self):
        self._upload_fixture_files()
        tag_import = MediaImporter('original', '')
        tag_import.import_media()

        self.assertEqual(MediumResized.objects.count(), 0)
        self.assertEqual(len(self._spi_s3_utils_processed.list_files('')), 0)

        medium = Medium.objects.filter(medium_type=Medium.VIDEO)[0]
        self.assertEqual(medium.file.md5, None)
        self.assertEqual(medium.duration, None)
        self.assertEqual(medium.height, None)
        self.assertEqual(medium.width, None)

        resizer = Resizer('processed', ['S', 'L'], 'Videos')
        resizer.resize_media()

        self.assertEqual(MediumResized.objects.count(), 2)
        self.assertEqual(len(self._spi_s3_utils_processed.list_files('')), 2)

        medium = Medium.objects.filter(medium_type=Medium.VIDEO)[0]
        self.assertEqual(medium.file.object_storage_key, 'MVI_0689_1.MOV')
        self.assertEqual(medium.file.md5, 'c116966f4d3da98b7ff03bf1abf238df')
        self.assertEqual(medium.file.size, 561627)
        self.assertEqual(medium.file.bucket, File.ORIGINAL)
        self.assertEqual(medium.width, 1920)
        self.assertEqual(medium.height, 1080)
        self.assertEqual(medium.duration, 1)
        self.assertEqual(medium.datetime_taken, None)   # Example video has no datetime

        small = MediumResized.objects.get(medium=medium, size_label="S")
        self.assertEqual(small.width, 640)
        self.assertEqual(small.height, 360)
        self.assertGreater(small.file.size, 30000)
        self.assertEqual(small.file.bucket, File.PROCESSED)

        large = MediumResized.objects.get(medium=medium, size_label="L")
        self.assertEqual(large.width, 1920)
        self.assertEqual(large.height, 1080)
        self.assertGreater(large.file.size, 80000)
        self.assertEqual(large.file.bucket, File.PROCESSED)
