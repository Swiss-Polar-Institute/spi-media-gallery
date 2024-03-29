import os

from django.conf import settings
from django.test import TestCase
from moto import mock_s3

from ..management.commands.add_files_with_tags import MediaImporter
from ..models import File, Medium, SpiS3Utils

# All the Boto S3 calls are mocked


class GenerateTagsTest(TestCase):
    fixtures = ["test_basic_data.yaml"]

    def __init__(self, *args, **kwargs) -> None:
        self._mock = mock_s3()
        self._mock.start()

        super().__init__(*args, **kwargs)

        # mock_s3 only works with the default endpoint
        settings.BUCKETS_CONFIGURATION["original"]["endpoint"] = None
        settings.BUCKETS_CONFIGURATION["processed"]["endpoint"] = None
        settings.BUCKETS_CONFIGURATION["imported"]["endpoint"] = None

        self._spi_s3_utils = SpiS3Utils("original")
        spi_s3_utils_resource = self._spi_s3_utils.resource()
        spi_s3_utils_resource.create_bucket(Bucket="spi-media-gallery-original")
        spi_s3_utils_resource.create_bucket(Bucket="spi-media-gallery-processed")
        spi_s3_utils_resource.create_bucket(Bucket="spi-media-gallery-imported")

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _upload_fixture_files(self) -> None:
        fixtures_buckets_original_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../fixtures/buckets/original"
        )

        for root, dirs, files in os.walk(fixtures_buckets_original_directory):
            for file in files:
                full_path_file = os.path.join(root, file)
                relative_directory_for_object_storage = root[
                    len(fixtures_buckets_original_directory) + 1 :
                ]
                key = os.path.join(relative_directory_for_object_storage, file)

                self._spi_s3_utils.upload_file(full_path_file, key)

    def test_add_files_with_tags(self):
        self._upload_fixture_files()
        self.assertEqual(Medium.objects.all().count(), 1)

        tag_import = MediaImporter("original", "")
        tag_import.import_media()

        self.assertEqual(Medium.objects.all().count(), 3)

        m = Medium.objects.get(file__object_storage_key="IMG_4329.jpg")
        m.file.bucket = File.PROCESSED
        tags = m.tags.all()

        self.assertEqual(tags.count(), 18)

        # There are more only testing a few of them
        tags_to_exist = ["people/john_doe", "people"]

        tags_names = [tag.name.name for tag in tags]

        for tag_to_exist in tags_to_exist:
            self.assertTrue(tag_to_exist in tags_names)

        # Replaces the XMP file to verify that new tags and removed tags are not there anymore
        full_path_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../fixtures",
            "IMG_4329-2.jpg.xmp",
        )
        self._spi_s3_utils.upload_file(full_path_file, "IMG_4329.jpg.xmp")

        tag_import = MediaImporter("original", "")
        tag_import.import_media()
        m = Medium.objects.get(file__object_storage_key="IMG_4329.jpg")
        new_tags = m.tags.all()

        # There is one less tag in the new XMP and this tag generated many tags earlier
        self.assertEqual(new_tags.count(), 11)

        new_tags_names = [tag.name.name for tag in new_tags]

        self.assertTrue("photographer/henry_lamar" in new_tags_names)
        self.assertTrue("photographer/emma_wright" not in new_tags_names)
