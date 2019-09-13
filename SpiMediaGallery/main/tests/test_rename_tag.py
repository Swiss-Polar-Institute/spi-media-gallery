from django.test import TestCase
from ..models import TagName
from ..management.commands.rename_tag import ModifyTag





class RenameTagTest(TestCase):
    fixtures = ['test_basic_data.yml']

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

        '''Check previous tag name exists in the database'''
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 1)

        '''Check new tag name does not exist in the database'''
        new_tag_name_count = TagName.objects.filter(name=new_tag).count()
        self.assertEqual(new_tag_name_count, 0)

        '''Do the renaming of the tag'''
        modifier = ModifyTag()

        modifier.rename(old_tag, new_tag)

        '''Check the old tag name does not exist in the database after the renaming'''
        old_tag_name_count = TagName.objects.filter(name=old_tag).count()
        self.assertEqual(old_tag_name_count, 0)

        '''Check new tag name does exist in the database after the renaming'''
        new_tag_name_count = TagName.objects.filter(name=new_tag).count()
        self.assertEqual(new_tag_name_count, 1)





