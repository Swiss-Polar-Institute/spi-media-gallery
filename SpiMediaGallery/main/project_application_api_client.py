import os
import tempfile
from datetime import datetime

import requests
from django.db import transaction

from SpiMediaGallery import settings
from main import spi_s3_utils
from main.models import File, Medium, License, Copyright
from main.utils import hash_of_file_path


class ProjectApplicationApiClient:
    def __init__(self, hostname, bucket_name):
        self._hostname = hostname
        self._bucket_name = bucket_name
        self._imported_bucket = spi_s3_utils.SpiS3Utils(bucket_name)

    def import_media_after(self, last_modified):
        headers = {'ApiKey': settings.PROJECT_APPLICATION_API_KEY}
        parameters = {}

        if last_modified:
            parameters['modified_since'] = last_modified
        else:
            parameters['modified_since'] = '1970-01-01T00:00:00+00:00'

        r = requests.get(f'{self._hostname}/api/media/list/', headers=headers, params=parameters)
        print(r.url)

        for medium in r.json():
            url = medium['file_url']
            download_request = requests.get(url, allow_redirects=True)

            output_file = tempfile.NamedTemporaryFile()
            output_file.write(download_request.content)

            print('Downloaded to:', output_file.name)

            output_file.flush()
            with transaction.atomic():
                object_storage_key = f'project_application/remote_id-{medium["id"]}'
                md5 = hash_of_file_path(output_file.name)
                file_size = os.stat(output_file.name).st_size

                self._imported_bucket.upload_file(output_file.name, object_storage_key)

                file = File.objects.create(object_storage_key=object_storage_key, md5=md5, size=file_size,
                                           bucket=File.IMPORTED)

                license, created = License.objects.get_or_create(spdx_identifier=medium['license'],
                                                                 defaults={'name': medium['license']})

                copyright, created = Copyright.objects.get_or_create(holder=medium['copyright'])
                Medium.objects.create(file=file, license=license, copyright=copyright, medium_type=Medium.PHOTO,
                                      datetime_imported=datetime.now())

            output_file.close()
