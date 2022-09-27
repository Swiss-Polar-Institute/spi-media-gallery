from django.test import TestCase

from main.delete_medium import DeleteMedium
from main.models import Copyright, File, Medium, Photographer, Tag, TagName


class DeleteMediumTest(TestCase):
    fixtures = ["test_basic_data.yaml"]

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_delete_medium(self):
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(Tag.objects.count(), 9)
        self.assertEqual(TagName.objects.count(), 9)
        self.assertEqual(Copyright.objects.count(), 1)

        photographer = Photographer.objects.get(id=1)

        medium = Medium.objects.get(id=1)
        medium.photographer = photographer
        medium.save()

        delete_medium = DeleteMedium(medium)
        delete_medium.delete()
        self.assertEqual(Medium.objects.all().count(), 0)

        # This unit test could test that objects that are not related are not being destroyed
        # Actually, thanks for the models.PROTECT in the models it would just fail instead of deleting them
        # (in case that it was tried to delete them)
        self.assertEqual(File.objects.count(), 0)

        # in the test_basic_data there are 9 tags and tagnames. 6 of them are assigned to the Medium
        # the other 3 are unused. Deleting the Medium deletes the assigned tags. Other tags are would need
        # to be checked using the check_integrity command or other means
        self.assertEqual(Tag.objects.count(), 3)
        self.assertEqual(TagName.objects.count(), 3)
        self.assertEqual(Copyright.objects.count(), 0)

        self.assertEqual(Photographer.objects.filter(id=1).exists(), False)
