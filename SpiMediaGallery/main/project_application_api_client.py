import os
import tempfile
from datetime import datetime
from django.utils import timezone

import dateutil.parser
import requests
from django.db import transaction

from SpiMediaGallery import settings
from main import spi_s3_utils, utils
from main.models import File, Medium, License, Copyright, RemoteMedium, Photographer
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
            parameters['modified_since'] = last_modified.isoformat()
        else:
            parameters['modified_since'] = '1970-01-01T00:00:00+00:00'

        r = requests.get(f'{self._hostname}/api/media/list/', headers=headers, params=parameters)
        print(r.url)

        for remote_medium_json in r.json():
            url = remote_medium_json['file_url']
            download_request = requests.get(url, allow_redirects=True)

            file_extension = utils.file_extension(remote_medium_json['original_file_path'])

            output_file = tempfile.NamedTemporaryFile(suffix=f'.{file_extension}')
            output_file.write(download_request.content)

            print('Downloaded to:', output_file.name)

            output_file.flush()
            with transaction.atomic():
                object_storage_key = f'project_application/remote_id-{remote_medium_json["id"]}.{file_extension}'
                md5 = hash_of_file_path(output_file.name)
                file_size = os.stat(output_file.name).st_size

                self._imported_bucket.upload_file(output_file.name, object_storage_key)

                file = File.objects.create(object_storage_key=object_storage_key, md5=md5, size=file_size,
                                           bucket=File.IMPORTED)

                license, created = License.objects.get_or_create(spdx_identifier=remote_medium_json['license'],
                                                                 defaults={'name': remote_medium_json['license'],
                                                                           'public_text': remote_medium_json['license']})

                copyright_holder = remote_medium_json['copyright']
                copyright, created = Copyright.objects.get_or_create(holder=copyright_holder)
                copyright.public_text = copyright_holder
                copyright.save()

                photographer_remote = remote_medium_json['photographer']
                photographer = Photographer.objects.create(first_name=photographer_remote['first_name'],
                                                                    last_name=photographer_remote['last_name'])

                medium = Medium.objects.create(file=file, license=license, copyright=copyright,
                                               photographer=photographer,
                                               datetime_imported=timezone.now(),
                                               medium_type=utils.get_type(file_extension)
                                               )

                project_info = remote_medium_json['project']
                project_key = project_info['key']
                project_title = project_info['title']

                tags = {f'Imported/Project Application/key/{project_key}',
                        f'Imported/Project Application/title/{project_title}'
                        }

                utils.set_tags(medium, tags)

                remote_modified_on = dateutil.parser.isoparse(remote_medium_json['modified_on'])

                RemoteMedium.objects.create(medium=medium, remote_id=remote_medium_json['id'],
                                            remote_modified_on=remote_modified_on,
                                            api_source=RemoteMedium.ApiSource.PROJECT_APPLICATION_API,
                                            remote_blob=str(remote_medium_json))

            output_file.close()
