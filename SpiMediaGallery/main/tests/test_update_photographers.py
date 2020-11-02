from django.test import TestCase
from ..models import Tag, Photographer, Medium
from ..management.commands.update_photographers import PhotographerUpdater


class PhotographerUpdaterTest(TestCase):
    fixtures = ['test_basic_data.yaml']

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_add_photographer_two_names(self):
        """Test the basic case of linking a medium to a photographer where the tag is given and the name of the photographer is in the photographer database table"""

        # Remove the other photography tag first (each medium can only be linked with one photographer)
        medium = Medium.objects.get(id=1)
        tag_to_delete = Tag.objects.get(id=9)
        print(medium.tags.all())
        medium.tags.remove(tag_to_delete)
        medium.save()
        print(medium.tags.all())

        tag = 'Photographer/John Doe'
        photographer = 'John Doe'

        # Check that the tag exists in the database
        tags = Tag.objects.filter(name__name=tag).count()
        self.assertEqual(tags, 1)

        # Check that the photographer exists in the database
        photographer_name = photographer.split(' ', 1)
        p_first_name = photographer_name[0]
        p_last_name = photographer_name[1]
        photographers = Photographer.objects.filter(first_name=p_first_name, last_name=p_last_name).count()
        self.assertEqual(photographers, 1)

        # Check that the medium does not have a photographer
        photographer = Photographer.objects.get(first_name=p_first_name, last_name=p_last_name)
        media = Medium.objects.filter(photographer=photographer).count()
        self.assertEqual(media, 0)

        # Do the update of the photographer name
        updater = PhotographerUpdater()
        updater.update()

        # Check that the medium is now linked to the photographer
        media_linked = Medium.objects.filter(photographer=photographer).count()
        self.assertEqual(media_linked, 1)

    def test_add_photographer_three_names(self):
        """Test the basic case of tagging a medium with a photographer when the photographer has three names (first name, two surnames)."""

        tag = 'Photographer/Alpha Surname Beta'
        photographer = 'Alpha Surname Beta'

        # Remove the other photography tag first (each medium can only be linked with one photographer)
        medium = Medium.objects.get(id=1)
        tag_to_delete = Tag.objects.get(id=8)
        print(medium.tags.all())
        medium.tags.remove(tag_to_delete)
        medium.save()
        print(medium.tags.all())

        # Check that the tag exists in the database
        tags = Tag.objects.filter(name__name=tag).count()
        self.assertEqual(tags, 1)

        # Check that the photographer exists in the database
        photographer_name = photographer.split(' ', 1)
        p_first_name = photographer_name[0]
        p_last_name = photographer_name[1]
        photographers = Photographer.objects.filter(first_name=p_first_name, last_name=p_last_name).count()
        self.assertEqual(photographers, 1)

        # Check that the medium does not have a photographer
        photographer = Photographer.objects.get(first_name=p_first_name, last_name=p_last_name)
        media = Medium.objects.filter(photographer=photographer).count()
        self.assertEqual(media, 0)

        # Do the update of the photographer name
        updater = PhotographerUpdater()
        updater.update()

        # Check that the medium is now linked to the photographer
        medium.refresh_from_db()
        # print(medium.tags.all())
        print(medium.photographer)
        media_linked = Medium.objects.filter(photographer=photographer).count()
        self.assertEqual(media_linked, 1)

