import os
import tempfile

from django.test import TestCase

from main.xmp_utils import XmpUtils


class XmpUtilsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(XmpUtilsTest, cls).setUpClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_read_write_tags(self):
        temporary_file = tempfile.NamedTemporaryFile(suffix=".xmp", delete=False)
        temporary_file.close()
        os.remove(temporary_file.name)

        tags = {'people', 'people/john_doe', 'vessel', 'penguin'}

        XmpUtils.generate_xmp(temporary_file.name, tags)

        read_tags = XmpUtils.read_tags(temporary_file.name)

        self.assertEquals(tags, read_tags)
