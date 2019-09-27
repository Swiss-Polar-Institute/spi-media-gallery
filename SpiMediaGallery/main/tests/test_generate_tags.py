from django.test import TestCase

from ..management.commands.generate_virtual_tags import GenerateTags
from ..models import *
import datetime


class GenerateTagsTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(GenerateTagsTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_delete_generated_tags_one(self):
        """Test the delete if there is only one Tag that is generated with that name"""

        # create a TagName that only has one Tag that is generated
        tag_name = TagName()
        tag_name.name = 'Person'
        tag_name.save()

        tag = Tag()
        tag.importer = Tag.GENERATED
        tag.name = tag_name
        tag.save()

        deleter = GenerateTags()
        deleter.delete_generated_tags()
        resulting_tags = Tag.objects.filter(name__name='Person').count()

        self.assertEqual(resulting_tags, 0)

    def test_delete_generated_tags_multiple(self):
        """Test the delete if there is more than one Tag with the same TagName and one of them is generated"""

        # create a TagName that has a Tag that is generated and another that is xmp
        tag_name = TagName()
        tag_name.name = 'Photographer'
        tag_name.save()

        tag = Tag()
        tag.importer = Tag.XMP
        tag.name = tag_name
        tag.save()

        tag = Tag()
        tag.importer = Tag.GENERATED
        tag.name = tag_name
        tag.save()

        deleter = GenerateTags()
        deleter.delete_generated_tags()
        resulting_tags = Tag.objects.filter(name__name='Photographer').count()

        self.assertEqual(resulting_tags, 1)

    def test_delete_generated_tags_with_media(self):

        tag_name = TagName()
        tag_name.name = 'Photographer'
        tag_name.save()

        tag_x = Tag()
        tag_x.importer = Tag.XMP
        tag_x.name = tag_name
        tag_x.save()

        tag_g = Tag()
        tag_g.importer = Tag.GENERATED
        tag_g.name = tag_name
        tag_g.save()

        medium = Medium()
        medium.datetime_imported = datetime.datetime.now()
        medium_type = medium.PHOTO
        medium.save()

        medium.tags.add(tag_x)
        medium.tags.add(tag_g)
        medium.save()

        deleter = GenerateTags()
        deleter.delete_generated_tags()
        resulting_tags = Tag.objects.filter(name__name='Photographer').count()
        resulting_tagged_media = Medium.objects.filter(tags__name__name='Photographer').count()

        self.assertEqual(resulting_tags, 1)
        self.assertEqual(resulting_tagged_media, 1)

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

