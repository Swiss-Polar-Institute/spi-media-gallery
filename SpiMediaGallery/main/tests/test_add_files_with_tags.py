from moto import mock_s3
from django.test import TestCase
from main.management.commands.add_files_with_tags import TagImporter
from main.spi_s3_utils import SpiS3Utils

from django.conf import settings
import os
import glob
from typing import List
from main.models import *

@mock_s3
class GenerateTagsTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(GenerateTagsTest, cls).setUpClass()
        # mock_s3 only works with the default endpoint
        settings.BUCKETS_CONFIGURATION["original"]["endpoint"] = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_files_with_tags(self):
        spi_s3_utils = SpiS3Utils("original")
        spi_s3_utils_resource = spi_s3_utils.resource()
        spi_s3_utils_resource.create_bucket(Bucket="photos")

        bucket_files_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../fixtures/buckets/original")

        files:[List[str]] = glob.glob(os.path.join(bucket_files_directory, "*"))

        for file in files:
            spi_s3_utils.upload_file(file, os.path.basename(file))

        self.assertEqual(Medium.objects.all().count(), 1)

        tag_import = TagImporter("original", "")
        tag_import.import_tags()

        self.assertEqual(Medium.objects.all().count(), 2)

        m = Medium.objects.get(file__object_storage_key="IMG_4329.jpg")
        tags = m.tags.all()

        self.assertEqual(tags.count(), 18)

        tags_to_exist = ["people/john_doe", "people"]

        tags_names = [tag.name.name for tag in tags]

        for tag_to_exist in tags_to_exist:
            self.assertTrue(tag_to_exist in tags_names)

