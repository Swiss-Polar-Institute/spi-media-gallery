from django.test import TransactionTestCase, TestCase
from main.models import *
import datetime
import pytz
from django.contrib.staticfiles.templatetags.staticfiles import static

from main.medium_for_view import MediumForView


class ImportSamplesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(ImportSamplesTest, cls).setUpClass()

        copyright = Copyright()
        copyright.holder = "EPFL"
        copyright.public_text = "Copyright by EPFL"
        copyright.save()

        medium = Medium()
        medium.datetime_imported = datetime.datetime(2019, 2, 3, 16, 43, 24, tzinfo=pytz.UTC)
        medium.medium_type = Medium.PHOTO
        medium.copyright = copyright
        medium.save()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_medium_for_view(self):
        medium_for_view = MediumForView.objects.all()[0]

        self.assertEqual(medium_for_view.copyright, None)

        self.assertEqual(medium_for_view.thumbnail_url(), static("images/thumbnail-does-not-exist.jpg"))
