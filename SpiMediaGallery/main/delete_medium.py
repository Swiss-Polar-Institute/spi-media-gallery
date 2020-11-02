from django.db import transaction

# Should this class be implemented from Medium.delete() ?
# Would we expect that Medium.delete() also deletes MediumResized, Tags, etc.?
from main.spi_s3_utils import SpiS3Utils


class DeleteMedium:
    def __init__(self, medium):
        self._medium = medium
        self._files_to_delete = []

    @staticmethod
    def _delete_tag_if_orphaned(tag):
        if not tag.medium_set.all().exists():
            print(f'Tag deleted: {tag}')
            tag.delete()
            return True

        return False

    @staticmethod
    def _delete_tag_name_if_orphaned(tag_name):
        if not tag_name.tag_set.all().exists():
            print(f'Tag name deleted: {tag_name}')
            tag_name.delete()

    @staticmethod
    def _delete_medium_and_file(medium):
        file = medium.file
        medium.delete()

        if file:
            bucket_name = file.bucket_name()
            object_storage_key = file.object_storage_key

            file.delete()

            spi_s3_utils = SpiS3Utils(bucket_name)
            spi_s3_utils.delete(object_storage_key)

    def delete(self):
        if self._medium is None:
            return

        with transaction.atomic():
            tags = list(self._medium.tags.all())

            for medium_resized in self._medium.mediumresized_set.all():
                DeleteMedium._delete_medium_and_file(medium_resized)

            self._medium.remotemedium_set.all().delete()

            DeleteMedium._delete_medium_and_file(self._medium)

            tag_names = []

            for tag in tags:
                if DeleteMedium._delete_tag_if_orphaned(tag):
                    tag_names.append(tag.name)

            for tag_name in tag_names:
                DeleteMedium._delete_tag_name_if_orphaned(tag_name)
