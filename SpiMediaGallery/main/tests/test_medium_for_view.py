from django.test import TransactionTestCase, TestCase
from main.models import *
import datetime
import pytz
from django.contrib.staticfiles.templatetags.staticfiles import static

from main.medium_for_view import MediumForView


class ImportSamplesTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(ImportSamplesTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_medium_for_view(self):
        medium_for_view = MediumForView.objects.all()[0]

        self.assertEqual(medium_for_view.copyright, Copyright.objects.filter(holder="EPFL")[0])

        self.assertEqual(medium_for_view.thumbnail_url(), static("images/thumbnail-does-not-exist.jpg"))

        self.assertEqual(medium_for_view.file_size_original(), "4.05 MB")

        self.assertEqual(medium_for_view.border_color(), None)

        self.assertEqual(medium_for_view.file_name(), "SPI-1.jpg")

        self.assertEqual(medium_for_view.list_of_tags(), [{'id': 1, 'tag': 'landscape'}])

        self.assertEqual(medium_for_view.license_text(), "Creative Commons 4.0")

        self.assertEqual(medium_for_view.photographer_name(), "Unknown")

        self.assertEqual(medium_for_view.is_photo(), True)

        self.assertEqual(medium_for_view.is_video(), False)
