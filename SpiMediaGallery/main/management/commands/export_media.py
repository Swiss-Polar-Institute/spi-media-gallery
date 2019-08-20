from django.core.management.base import BaseCommand, CommandError

from main.models import Tag

from main.spi_s3_utils import SpiS3Utils
from main.medium_for_view import MediumForView
from main.progress_report import ProgressReport
from main.xmp_utils import XmpUtils
import os


class Command(BaseCommand):
    help = 'Exports resized media with generated XMP files'

    def add_arguments(self, parser):
        parser.add_argument('prefix', type=str, help="Prefix - can be ''")
        parser.add_argument('output_directory', type=str, help="Output of the resized media with the XMP associated files")
        parser.add_argument('size', type=str, choices=["S", "L", "O"], help="Size (Small, Large, Original files) to be exported")

    def handle(self, *args, **options):
        prefix = options["prefix"]
        output_directory = options["output_directory"]
        size = options["size"]

        export_media = ExportMedia(prefix, output_directory, size)

        export_media.run()


class ExportMedia(object):
    def __init__(self, prefix, output_directory, size):
        self._prefix = prefix
        self._output_directory = output_directory
        self._size = size

        self._resizes_bucket = SpiS3Utils("processed")

    def run(self):
        if os.path.exists(self._output_directory):
            raise CommandError("output_directory ({}) should not exist".format(self._output_directory))

        try:
            os.makedirs(self._output_directory)
        except (PermissionError, FileExistsError) as e:
            raise CommandError("Can't create {}".format(self._output_directory))

        media = MediumForView.objects.filter(file__object_storage_key__startswith=self._prefix)
        progress_report = ProgressReport(media.count())

        for medium in media:
            progress_report.increment_and_print_if_needed()

            medium_resized = medium._medium_resized(self._size)

            if medium_resized is None or medium_resized.file is None:
                print("Medium without the resized file")
                continue

            tags = medium_resized.medium.tags.all()
            tags_list = []
            for tag in tags:
                if tag.importer != Tag.GENERATED:
                    tags_list.append(tag.name)

            object_storage_key_relative_directory = medium.file.object_storage_key.lstrip("/")
            output_file = os.path.join(self._output_directory, object_storage_key_relative_directory)

            self._resizes_bucket.download_file(medium_resized.file.object_storage_key, output_file, create_directory=True)
            XmpUtils.generate_xmp(output_file + ".xmp", tags_list)

        print("Output: {}".format(self._output_directory))