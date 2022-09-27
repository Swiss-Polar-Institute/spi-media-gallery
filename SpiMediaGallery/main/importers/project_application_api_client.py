import os
import tempfile

import dateutil.parser
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from main import spi_s3_utils, utils
from main.delete_medium import DeleteMedium
from main.utils import hash_of_file_path
from SpiMediaGallery import settings

from ..management.commands.generate_virtual_tags import GenerateTags

from main.models import (  # isort:skip
    Copyright,
    File,
    License,
    Medium,
    Photographer,
    RemoteMedium,
    SyncToken,
    Tag,
)


class ProjectApplicationApiClient:
    _OLDER_LAST_SYNC_POSSIBLE = "1970-01-01T00:00:00+00:00"

    def __init__(self):
        self._hostname = settings.PROJECT_APPLICATION_BASE_URL
        self._imported_bucket = spi_s3_utils.SpiS3Utils(bucket_name="imported")

    @staticmethod
    def _latest_modified_time(Model):
        try:
            latest_remote_date_time = Model.objects.latest(
                "remote_modified_on"
            ).remote_modified_on
        except ObjectDoesNotExist:
            latest_remote_date_time = (
                ProjectApplicationApiClient._OLDER_LAST_SYNC_POSSIBLE
            )

        return latest_remote_date_time

    def import_new_media(self):
        """Returns list of tags of the imported media"""
        headers = {"ApiKey": settings.PROJECT_APPLICATION_API_KEY}
        parameters = {}

        last_modified = ProjectApplicationApiClient._latest_modified_time(RemoteMedium)

        parameters["modified_since"] = last_modified

        r = requests.get(
            f"{self._hostname}/api/media/list/", headers=headers, params=parameters
        )

        imported_media = set()
        generator = GenerateTags()

        for remote_medium_json in r.json():
            url = remote_medium_json["file_url"]
            download_request = requests.get(url, allow_redirects=True)

            file_extension = utils.get_file_extension(
                remote_medium_json["original_file_path"]
            )

            output_file = tempfile.NamedTemporaryFile(suffix=f".{file_extension}")
            output_file.write(download_request.content)
            output_file.flush()

            remote_id = remote_medium_json["id"]
            print(f"Importing remote_id: {remote_id}")

            try:
                remote_medium = RemoteMedium.objects.get(
                    remote_id=remote_id,
                    api_source=RemoteMedium.ApiSource.PROJECT_APPLICATION_API,
                )
                medium = remote_medium.medium
            except ObjectDoesNotExist:
                remote_medium = None
                medium = None

            with transaction.atomic():
                object_storage_key = f'project_application/remote_id-{remote_medium_json["id"]}.{file_extension}'
                md5 = hash_of_file_path(output_file.name)
                remote_file_md5 = remote_medium_json["file_md5"]

                assert md5 == remote_file_md5

                file_size = os.stat(output_file.name).st_size

                self._imported_bucket.upload_file(output_file.name, object_storage_key)

                file = File.objects.create(
                    object_storage_key=object_storage_key,
                    md5=md5,
                    size=file_size,
                    bucket=File.IMPORTED,
                )

                remote_license = remote_medium_json["license"]

                if remote_license:
                    license, created = License.objects.get_or_create(
                        name=remote_license, defaults={"public_text": remote_license}
                    )
                else:
                    license = None

                photographer_remote = remote_medium_json["photographer"]
                photographer, created = Photographer.objects.get_or_create(
                    first_name=photographer_remote["first_name"],
                    last_name=photographer_remote["last_name"],
                )

                copyright_holder = remote_medium_json["copyright"]
                if not copyright_holder:
                    copyright_holder = photographer.full_name()
                copyright, created = Copyright.objects.get_or_create(
                    holder=copyright_holder
                )
                copyright.public_text = copyright_holder
                copyright.save()

                medium_fields = {
                    "file": file,
                    "license": license,
                    "copyright": copyright,
                    "photographer": photographer,
                    "datetime_imported": timezone.now(),
                    "medium_type": utils.get_type(file_extension),
                }

                if medium:
                    medium.update_fields(medium_fields)
                    medium.save()
                else:
                    medium = Medium.objects.create(**medium_fields)

                project_info = remote_medium_json["project"]
                project_key = project_info["key"]
                funding_instrument = project_info["funding_instrument"]
                finance_year = project_info["finance_year"]

                tags = {
                    f"SPI Project/{funding_instrument}/{finance_year}/key/{project_key}",
                    f"Photographer/{photographer.full_name()}",
                }

                old_tags = set(medium.tags.all())
                utils.set_tags(medium, tags, Tag.IMPORTED)
                new_tags = set(medium.tags.all())

                remote_modified_on = dateutil.parser.isoparse(
                    remote_medium_json["modified_on"]
                )

                remote_medium_fields = {}
                remote_medium_fields["medium"] = medium
                remote_medium_fields["remote_id"] = remote_id
                remote_medium_fields[
                    "api_source"
                ] = RemoteMedium.ApiSource.PROJECT_APPLICATION_API
                remote_medium_fields["remote_blob"] = str(remote_medium_json)
                remote_medium_fields["remote_modified_on"] = remote_modified_on

                if remote_medium is None:
                    remote_medium = RemoteMedium.objects.create(**remote_medium_fields)
                else:
                    remote_medium.update_fields(remote_medium_fields)
                    remote_medium.save()

                generator.generate_tags_for_medium(medium)
                imported_media.add(medium)

                deleted_tags = old_tags - new_tags
                generator.delete_tags_if_orphaned(deleted_tags)

            output_file.close()

        return imported_media

    def delete_deleted_media(self):
        """Returns list of tags of the deleted media"""
        headers = {"ApiKey": settings.PROJECT_APPLICATION_API_KEY}
        parameters = {}

        try:
            last_deleted_media_token = SyncToken.objects.get(
                token_name=SyncToken.TokenNames.DELETED_MEDIA_LAST_SYNC
            ).token_value
        except ObjectDoesNotExist:
            last_deleted_media_token = (
                ProjectApplicationApiClient._OLDER_LAST_SYNC_POSSIBLE
            )

        parameters["modified_since"] = last_deleted_media_token

        r = requests.get(
            f"{self._hostname}/api/media/list/deleted/",
            headers=headers,
            params=parameters,
        )

        newer_last_deleted = last_deleted_media_token

        tags_deleted = set()

        for remote_medium_deleted_json in r.json():
            remote_id = remote_medium_deleted_json["id"]
            deleted_on = remote_medium_deleted_json["deleted_on"]

            try:
                remote_medium = RemoteMedium.objects.get(remote_id=remote_id)
                medium = remote_medium.medium
            except ObjectDoesNotExist:
                # The Project Application Medium was created and deleted before SPI Media Gallery ever imported it
                continue

            tags_deleted.update(medium.tags.all())

            delete_medium = DeleteMedium(medium)
            delete_medium.delete()

            if deleted_on > newer_last_deleted:
                newer_last_deleted = deleted_on

        SyncToken.objects.update_or_create(
            token_name=SyncToken.TokenNames.DELETED_MEDIA_LAST_SYNC,
            defaults={"token_value": newer_last_deleted},
        )

        return tags_deleted
