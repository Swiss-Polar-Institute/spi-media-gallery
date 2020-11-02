from django.db import transaction, DatabaseError

# Should this class be implemented from Medium.delete() ?
# Would we expect that Medium.delete() also deletes MediumResized, Tags, etc.?
from main.spi_s3_utils import SpiS3Utils


class DeleteMedium:
    def __init__(self, medium):
        self._medium = medium
        self._files_to_delete = []

    @staticmethod
    def _delete_instance_if_orphaned(obj):
        if obj is None:
            return

        if hasattr(obj, 'medium_set'):
            fk = 'medium_set'
        elif hasattr(obj, 'tag_set'):
            fk = 'tag_set'
        else:
            assert False

        if not getattr(obj, fk).all().exists():
            obj.delete()
            return True
        return False

    def _delete_medium_and_file(self, medium):
        file = medium.file
        medium.delete()

        if file:
            self._files_to_delete.append(
                {'bucket_name': file.bucket_name(),
                 'object_storage_key': file.object_storage_key
                 })
            file.delete()

    def delete(self):
        if self._medium is None:
            return

        transaction_success = True
        try:
            with transaction.atomic():
                tags = list(self._medium.tags.all())
                copyright = self._medium.copyright
                photographer = self._medium.photographer

                for medium_resized in self._medium.mediumresized_set.all():
                    self._delete_medium_and_file(medium_resized)

                self._medium.remotemedium_set.all().delete()

                self._delete_medium_and_file(self._medium)

                DeleteMedium._delete_instance_if_orphaned(copyright)
                DeleteMedium._delete_instance_if_orphaned(photographer)

                tag_names = []

                for tag in tags:
                    if DeleteMedium._delete_instance_if_orphaned(tag):
                        tag_names.append(tag.name)

                for tag_name in tag_names:
                    DeleteMedium._delete_instance_if_orphaned(tag_name)

        except DatabaseError:
            transaction_success = False

        if transaction_success:
            for file_to_delete in self._files_to_delete:
                spi_s3_utils = SpiS3Utils(file_to_delete['bucket_name'])
                spi_s3_utils.delete(file_to_delete['object_storage_key'])
