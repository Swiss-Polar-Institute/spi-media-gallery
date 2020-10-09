import os
import tempfile

import dateutil.parser
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from SpiMediaGallery import settings
from main import spi_s3_utils, utils
from main.models import File, Medium, License, Copyright, RemoteMedium, Photographer
from main.utils import hash_of_file_path


class ProjectApplicationApiClient:
    def __init__(self, ):
        self._hostname = settings.PROJECT_APPLICATION_BASE_URL
        self._imported_bucket = spi_s3_utils.SpiS3Utils(bucket_name='imported')

    @staticmethod
    def _latest_modified_time():
        try:
            latest_remote_date_time = RemoteMedium.objects.latest('remote_modified_on').remote_modified_on
        except ObjectDoesNotExist:
            latest_remote_date_time = '1970-01-01T00:00:00+00:00'

        return latest_remote_date_time

    def import_new_media(self):
        headers = {'ApiKey': settings.PROJECT_APPLICATION_API_KEY}
        parameters = {}

        last_modified = ProjectApplicationApiClient._latest_modified_time()

        parameters['modified_since'] = last_modified

        r = requests.get(f'{self._hostname}/api/media/list/', headers=headers, params=parameters)

        for remote_medium_json in r.json():
            url = remote_medium_json['file_url']
            download_request = requests.get(url, allow_redirects=True)

            file_extension = utils.get_file_extension(remote_medium_json['original_file_path'])

            output_file = tempfile.NamedTemporaryFile(suffix=f'.{file_extension}')
            output_file.write(download_request.content)
            output_file.flush()

            remote_id = remote_medium_json['id']
            print(f'Importing remote_id: {remote_id}')

            try:
                remote_medium = RemoteMedium.objects.get(remote_id=remote_id,
                                                         api_source=RemoteMedium.ApiSource.PROJECT_APPLICATION_API)
                medium = remote_medium.medium
            except ObjectDoesNotExist:
                remote_medium = None
                medium = None

            with transaction.atomic():
                object_storage_key = f'project_application/remote_id-{remote_medium_json["id"]}.{file_extension}'
                md5 = hash_of_file_path(output_file.name)
                file_size = os.stat(output_file.name).st_size

                self._imported_bucket.upload_file(output_file.name, object_storage_key)

                file = File.objects.create(object_storage_key=object_storage_key, md5=md5, size=file_size,
                                           bucket=File.IMPORTED)

                license, created = License.objects.get_or_create(spdx_identifier=remote_medium_json['license'],
                                                                 defaults={'name': remote_medium_json['license'],
                                                                           'public_text': remote_medium_json[
                                                                               'license']})

                photographer_remote = remote_medium_json['photographer']
                photographer, created = Photographer.objects.get_or_create(first_name=photographer_remote['first_name'],
                                                                           last_name=photographer_remote['last_name'])

                copyright_holder = remote_medium_json['copyright']
                if not copyright_holder:
                    copyright_holder = photographer.full_name()
                copyright, created = Copyright.objects.get_or_create(holder=copyright_holder)
                copyright.public_text = copyright_holder
                copyright.save()

                medium_fields = {'file': file,
                                 'license': license,
                                 'copyright': copyright,
                                 'photographer': photographer,
                                 'datetime_imported': timezone.now(),
                                 'medium_type': utils.get_type(file_extension)
                                 }

                if medium:
                    medium.update_fields(medium_fields)
                    medium.save()
                else:
                    medium = Medium.objects.create(**medium_fields)

                project_info = remote_medium_json['project']
                project_key = project_info['key']
                project_title = project_info['title']

                tags = {f'Imported/Project Application/key/{project_key}',
                        f'Imported/Project Application/title/{project_title}'
                        }

                utils.set_tags(medium, tags)

                remote_modified_on = dateutil.parser.isoparse(remote_medium_json['modified_on'])

                remote_medium_fields = {}
                remote_medium_fields['medium'] = medium
                remote_medium_fields['remote_id'] = remote_id
                remote_medium_fields['api_source'] = RemoteMedium.ApiSource.PROJECT_APPLICATION_API
                remote_medium_fields['remote_blob'] = str(remote_medium_json)
                remote_medium_fields['remote_modified_on'] = remote_modified_on

                if remote_medium is None:
                    remote_medium = RemoteMedium.objects.create(**remote_medium_fields)
                else:
                    remote_medium.update_fields(remote_medium_fields)
                    remote_medium.save()

            output_file.close()
