from django.test import TestCase
from ..models import Tag, Medium
from ..management.commands.add_tag_to_media import AssignTag

class RenameTagTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    @classmethod
    def setUpClass(cls):
        super(RenameTagTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_assign_tag_to_one_file(self):
        """Assign a new tag to one file using its object storage key, where tag already exists. """

        object_storage_key = 'disk1/test01.jpg'
        tagname = 'Aerial'

        assigner = AssignTag()
        assigner.add_tag(object_storage_key, tagname, False)

        # Check tag exists or has been created
        tags = Tag.objects.filter(name__name=tagname)
        tag_count = Tag.objects.filter(name__name=tagname, importer=Tag.MANUAL).count()
        self.assertEqual(tag_count, 1)

        # Get tag's id
        tag = Tag.objects.get(name__name=tagname, importer=Tag.MANUAL)
        tag_id = tag.id

        # Get the medium from the object storage
        medium = Medium.objects.get(file__object_storage_key=object_storage_key)
        medium_id = medium.id

        # Check that the tag has been assigned
        self.assertTrue(tag in medium.tags.all())

        medium_tag_count = medium.tags.filter(id=tag_id).count()
        self.assertEqual(medium_tag_count, 1)

