from django.test import TestCase
from ..models import TagName, TagRenamed, Tag
from ..management.commands.rename_tag import ModifyTag
from ..views import search_for_tag_name_ids





class RenameTagTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(RenameTagTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_rename_tag_destination_tag_does_not_exist(self):
        old_tag = 'people/john_doe'
        new_tag = 'people/james_door'

        # Check that no tags have been renamed
        self.assertEqual(TagRenamed.objects.count(), 0)

        # Check previous tag name exists in the database
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 1)

        # Get the id of the old tag name
        old_id = TagName.objects.get(name=old_tag).id

        # Get the media tagged with the old tag name
        old_media_ids = set(search_for_tag_name_ids([old_id])[1].values_list('id', flat=True))

        # Check new tag name does not exist in the database
        new_tag_name_count = TagName.objects.filter(name=new_tag).count()
        self.assertEqual(new_tag_name_count, 0)

        # Do the renaming of the tag
        modifier = ModifyTag()

        modifier.rename(old_tag, new_tag)

        # Check the old tag name does not exist in the database after the renaming
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 0)

        # Check new tag name does exist in the database after the renaming
        new_tag_name_count = TagName.objects.filter(name=new_tag).count()
        self.assertEqual(new_tag_name_count, 1)

        # Get the id of the new tag name
        new_id = TagName.objects.get(name=new_tag).id

        # Get the media tagged with the new tag name
        new_media_ids = set(search_for_tag_name_ids([new_id])[1].values_list('id', flat=True))

        # Check that the new tag name has the same id as the old tag name
        self.assertEqual(old_id, new_id)

        # Check that the media tagged with the old and new tag names are the same
        self.assertSetEqual(old_media_ids, new_media_ids)

        # Check that the renaming of the tag has been added to the TagRenamed table
        self.assertEqual(TagRenamed.objects.filter(old_name=old_tag, new_name=new_tag).count(), 1)

    def test_rename_tag_destination_tag_does_exist(self):

        old_tag = 'people/john_doe'
        new_tag = 'people/john_dawes'

        # Check that no tags have been renamed
        self.assertEqual(TagRenamed.objects.count(), 0)

        # Check old tag name exists in the database
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 1)

        # Check new tag name exists in the database
        new_tag_name_count = TagName.objects.filter(name=new_tag).count()
        self.assertEqual(new_tag_name_count, 1)

        # Get the id of the old tag name
        old_id = TagName.objects.get(name=old_tag).id

        # Get the id of the new tag name
        new_id = TagName.objects.get(name=new_tag).id

        # Check that the tag name ids are different
        self.assertNotEqual(old_id, new_id)

        # Get the media tagged with the old tag name before renaming
        old_media_ids_before_renaming = set(search_for_tag_name_ids([old_id])[1].values_list('id', flat=True))

        # Get the media tagged with the new tag name before renaming
        new_media_ids_before_renaming = set(search_for_tag_name_ids([new_id])[1].values_list('id', flat=True))

        ### Get the media that are the union of old and new tags (the media that are already tagged by both)
        media_tagged_both_tags_before = old_media_ids_before_renaming.union(new_media_ids_before_renaming)

        # Do the renaming of the tag
        modifier = ModifyTag()

        modifier.rename(old_tag, new_tag)

        # Check the old tag name does not exist in the database after the renaming
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 0)

        old_tag_count = Tag.objects.filter(name__name=old_tag).count()
        self.assertEqual(old_tag_count, 0)

        # Check new tag name does exist in the database after the renaming
        new_tag_name_count = Tag.objects.filter(name__name=new_tag, importer=Tag.RENAMED).count()
        self.assertEqual(new_tag_name_count, 1)

        # Get the media tagged with the new tag name after renaming
        new_media_ids_after_renaming = set(search_for_tag_name_ids([new_id])[1].values_list('id', flat=True))

        # Check that the media tagged with both tag names before are now tagged with the new tag name
        self.assertSetEqual(media_tagged_both_tags_before, new_media_ids_after_renaming)

        # Check that the renaming of the tag has been added to the TagRenamed table
        self.assertEqual(TagRenamed.objects.filter(old_name=old_tag, new_name=new_tag).count(), 1)




