import os
import tempfile

from django.test import TestCase

from ..xmp_utils import XmpUtils


class XmpUtilsTest(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_read_write_tags(self):
        # Creates XMP file with certain tags
        temporary_file = tempfile.NamedTemporaryFile(suffix=".xmp", delete=False)
        temporary_file.close()
        os.remove(temporary_file.name)

        tags = {"people", "people/john_doe", "vessel", "penguin"}

        XmpUtils.generate_xmp(temporary_file.name, tags)

        # Reads the tags of the generated XMP file
        read_tags = XmpUtils.read_tags(temporary_file.name)

        # asserts that the original tags and read tags are the same
        self.assertEquals(tags, read_tags)

        os.unlink(temporary_file.name)
