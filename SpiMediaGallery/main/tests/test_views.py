from datetime import datetime

from django.conf import settings
from django.test import Client, TestCase
from moto import mock_s3

from main.models import Medium
from main.utils import SpiS3Utils


class ViewsTest(TestCase):
    fixtures = ["test_basic_data.yaml"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        settings.BUCKETS_CONFIGURATION["imported"]["endpoint"] = None

    def setUp(self):
        self._mock = mock_s3()
        self._mock.start()

        self._spi_s3_utils_imported = SpiS3Utils("imported")
        spi_s3_utils_resource_imported = self._spi_s3_utils_imported.resource()
        spi_s3_utils_resource_imported.create_bucket(
            Bucket="spi-media-gallery-imported"
        )

    def tearDown(self):
        pass

    def test_homepage(self):
        c = Client()

        response = c.get("/")

        self.assertEqual(response.status_code, 200)

    def test_medium_not_found(self):
        c = Client()

        response = c.get("/media/9999999")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Media not found", status_code=404)

    def test_medium(self):
        c = Client()

        response = c.get("/media/1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SPI-1.jpg")
        self.assertContains(response, "Copyright EPFL")

    def test_search_invalid_parameters(self):
        c = Client()

        response = c.get("/media/?invalid_parameter=1")

        self.assertEqual(response.status_code, 400)

    def test_search(self):
        c = Client()

        response = c.get("/media/?tags=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tag: landscape (1 results)")

    def test_upload(self):
        c = Client()

        with open("main/fixtures/buckets/original/IMG_4329.jpg", "rb") as fp:
            response = c.post(
                "/api/v1/medium/",
                {
                    "datetime_taken": "2002-02-02",
                    "medium_type": "P",
                    "people": "fred",
                    "project": "joe",
                    "photographer_value": "bar",
                    "copyright": "Ducati",
                    "license": "900SS",
                    "tags_value": ["Landscape", "Landscape/test"],
                    "file": fp,
                },
            )

        self.assertEqual(201, response.status_code)
        m = Medium.objects.get(file__object_storage_key="IMG_4329.jpg")
        new_tags = m.tags.all()
        self.assertEqual(m.file.object_storage_key, "IMG_4329.jpg")
        self.assertEqual(
            m.datetime_taken, datetime.strptime("2002-02-02 +0000", "%Y-%m-%d %z")
        )
        self.assertEqual(m.medium_type, "P")
        self.assertEqual(new_tags.count(), 4)
