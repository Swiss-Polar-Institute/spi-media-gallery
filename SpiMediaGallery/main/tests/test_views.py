from django.test import TestCase
from main.models import *
from django.contrib.staticfiles.templatetags.staticfiles import static

from main.views import Homepage

from django.test import Client

class ViewsTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(ViewsTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_homepage(self):
        c = Client()

        response = c.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "landscape")

        self.assertNotContains(response, "this is not a tag")
        self.assertContains(response, "landscape")
