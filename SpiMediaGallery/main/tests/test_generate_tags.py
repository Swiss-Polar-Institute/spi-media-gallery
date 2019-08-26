from django.test import TestCase

from ..management.commands.generate_virtual_tags import GenerateTags
from ..models import *


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
        tags_qs = Medium.objects.get(id=1).tags.all()

        self.assertTrue(tags_qs.get(name__name='landscape', importer=Tag.XMP))
        self.assertTrue(tags_qs.get(name__name='people/john_doe', importer=Tag.XMP))

        generator = GenerateTags()
        generator.generate_tags()

        tags_qs = Medium.objects.get(id=1).tags
        self.assertTrue(tags_qs.get(name__name='landscape', importer=Tag.XMP))
        self.assertTrue(tags_qs.get(name__name='people/john_doe', importer=Tag.XMP))
        self.assertTrue(tags_qs.get(name__name='people', importer=Tag.GENERATED))

