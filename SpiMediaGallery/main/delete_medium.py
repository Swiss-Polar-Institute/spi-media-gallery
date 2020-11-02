from django.db import transaction


# Should this class be implemented from Medium.delete() ?
# Would we expect that Medium.delete() also deletes MediumResized, Tags, etc.?

class DeleteMedium:
    def __init__(self, medium):
        self._medium = medium

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

    def delete(self):
        with transaction.atomic():
            tags = list(self._medium.tags.all())

            self._medium.mediumresized_set.all().delete()
            self._medium.remotemedium_set.all().delete()
            self._medium.delete()

            tag_names = []

            for tag in tags:
                if DeleteMedium._delete_tag_if_orphaned(tag):
                    tag_names.append(tag.name)

            for tag_name in tag_names:
                DeleteMedium._delete_tag_name_if_orphaned(tag_name)
