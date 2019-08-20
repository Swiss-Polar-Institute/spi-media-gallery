import os
import tempfile

from django.core.management.base import BaseCommand, CommandError

from main import spi_s3_utils
from main import utils
from main.models import Medium
from main.progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Updates datetime_taken'

    def handle(self, *args, **options):
        update_time = UpdateTime()
        update_time.update_time()


class UpdateTime(object):
    def __init__(self):
        self._media_bucket = spi_s3_utils.SpiS3Utils("original")

    def update_time(self):
        media = Medium.objects.filter(width__isnull=False).filter(datetime_taken__isnull=True)

        if len(media) == 0:
            CommandError("Nothing to be datetime_taken updated")

        progress_report = ProgressReport(len(media), unit="file",
                                         extra_information="Update datetime_taken")

        for medium in media:
            # Download Media file from the bucket
            suffix = utils.file_extension(medium.file.object_storage_key)
            local_media_file = tempfile.NamedTemporaryFile(suffix="." + suffix, delete=False)
            local_media_file.close()
            self._media_bucket.bucket().download_file(medium.file.object_storage_key, local_media_file.name)

            assert os.stat(local_media_file.name).st_size == medium.file.size

            information = utils.get_medium_information(local_media_file.name)

            if 'datetime_taken' in information:
                medium.datetime_taken = information['datetime_taken']

                medium.save()

            print("Finished: medium.id: {}".format(medium.id))

            os.remove(local_media_file.name)

            progress_report.increment_and_print_if_needed()
