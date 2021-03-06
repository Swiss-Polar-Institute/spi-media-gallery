# import datetime
#
# import pytz
# from django.contrib.staticfiles.templatetags.staticfiles import static
# from django.test import TestCase
#
# from ..medium_for_view import MediumForView
# from ..models import *
#
#
# class ImportSamplesTest(TestCase):
#     fixtures = ['test_basic_data.yaml']
#
#     @classmethod
#     def setUpClass(cls):
#         super(ImportSamplesTest, cls).setUpClass()
#
#     def setUp(self):
#         pass
#
#     def tearDown(self):
#         pass
#
#     def test_general(self):
#         medium_for_view = MediumForView.objects.all()[0]
#
#         self.assertEqual(medium_for_view.copyright, Copyright.objects.filter(holder='EPFL')[0])
#
#         self.assertEqual(medium_for_view.thumbnail_url(), static('images/thumbnail-does-not-exist.jpg'))
#
#         self.assertEqual(medium_for_view.file_size_original(), '4.05 MB')
#
#         self.assertEqual(medium_for_view.border_color(), None)
#
#         self.assertEqual(medium_for_view.file_name(), 'SPI-1.jpg')
#
#         self.assertEqual(medium_for_view.list_of_tags(),
#                          [{'id': 1, 'tag': 'landscape'}, {'id': 3, 'tag': 'people/john_doe'}])
#
#         self.assertEqual(medium_for_view.license_text(), 'Creative Commons 4.0')
#
#         self.assertEqual(medium_for_view.photographer_name(), 'Unknown')
#
#         self.assertEqual(medium_for_view.is_photo(), True)
#
#         self.assertEqual(medium_for_view.is_video(), False)
#
#     def test_author(self):
#         medium_for_view = MediumForView.objects.all()[0]
#
#         photographer = Photographer(first_name='John', last_name='Doe')
#         photographer.save()
#
#         medium_for_view.photographer = photographer
#
#         medium_for_view.save()
#
#         self.assertEqual(medium_for_view.photographer_name(), 'John Doe')
#
#     def test_medium_thumbnail_type(self):
#         medium_for_view = MediumForView()
#
#         medium_for_view.medium_type = 'P'
#         medium_for_view.datetime_imported = datetime.datetime.now().replace(tzinfo=pytz.utc)
#
#         self.assertEqual(medium_for_view.thumbnail_type(), 'P')
#
#         medium_for_view.medium_type = 'V'
#         medium_for_view.save()
#
#         # Resized file doesn't exist (e.g. it could no be resized), it returns a Photo because
#         # the thumbnail is going to be a JPEG placeholder
#         self.assertEqual(medium_for_view.thumbnail_type(), 'P')
#
#         file = File()
#         file.object_storage_key = 'test.webm'
#         file.bucket = File.PROCESSED
#         file.md5 = '6b985f9241fecb23fabb5206df731329'
#         file.size = 2420424
#         file.save()
#
#         resized = MediumResized()
#         resized.size_label = 'S'
#         resized.datetime_resized = datetime.datetime.now().replace(tzinfo=pytz.UTC)
#         resized.width = 800
#         resized.height = 600
#         resized.file = file
#         resized.medium = medium_for_view
#         resized.save()
#
#         self.assertEqual(medium_for_view.thumbnail_type(), 'V')
