from django.core.management import CommandError
from django.test import TestCase

from main.management.commands.delete_tag import DeleteTag
from main.models import TagName


class DeleteTagTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(DeleteTagTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_delete_tag(self):
        """Test the basic case, that a tag can be deleted and no longer exists in the database afterwards."""

        tag_name = 'people/john_doe'

        # Do the deletion of the tag
        deleter = DeleteTag()
        deleter.delete(tag_name)

        tag_name_count = TagName.objects.filter(name=tag_name).count()
        self.assertEqual(tag_name_count, 0)

    def test_delete_tag_does_not_exist(self):
        """Test the case where the tag does not exist in the database. Returns a list of tags not deleted."""

        tag_name = 'people/no_name'

        expected_list = ['people/no_name']

        # Try to do the deletion of the tag
        deleter = DeleteTag()
        deleter.delete(tag_name)

        tags_not_deleted = deleter.tags_not_deleted()

        self.assertListEqual(tags_not_deleted, expected_list)

    def test_raise_error_if_generated_tag(self):
        """Test that an error is raised if the tag if it has an importer GENERATED"""

        tag_name = 'people'

        with self.assertRaises(CommandError):
            DeleteTag._raise_error_if_generated_tag(tag_name)

