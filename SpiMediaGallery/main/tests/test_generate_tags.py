from main.management.commands.generate_virtual_tags import GenerateTags
from main.models import *

from django.test import TestCase


class GenerateTagsTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(GenerateTagsTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_generate_tags(self):
        tags_qs = Medium.objects.get(id=1).tags

        self.assertTrue(tags_qs.get(tag="landscape", importer=Tag.XMP))
        self.assertTrue(tags_qs.get(tag="people/john_doe", importer=Tag.XMP))

        generator = GenerateTags()
        generator.generate_tags()

        tags_qs = Medium.objects.get(id=1).tags
        self.assertTrue(tags_qs.get(tag="landscape", importer=Tag.XMP))
        self.assertTrue(tags_qs.get(tag="people/john_doe", importer=Tag.XMP))
        self.assertTrue(tags_qs.get(tag="people", importer=Tag.GENERATED))
