from django.core.management.base import BaseCommand

from main.models import Medium, Photographer

from main.progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Updates photographer of photos based on Photographer tag'

    def handle(self, *args, **options):
        photographer_updater = PhotographerUpdater()

        photographer_updater.update()


class PhotographerUpdater(object):
    def __init__(self):
        pass

    def update(self):
        photos_without_photographer = Medium.objects.filter(photographer__isnull=True)

        progress_report = ProgressReport(len(photos_without_photographer), extra_information="Updating photographer of photos")

        for photo in photos_without_photographer:
            progress_report.increment_and_print_if_needed()

            photographer_str = self._get_photographer_string(photo.tags.all())

            if photographer_str is None:
                print("Photo without photographer tag:", photo.object_storage_key)
                continue

            photographer = self._get_photographer(photographer_str)

            photo.photographer = photographer
            photo.save()

    @staticmethod
    def _get_photographer(string):
        first_name, last_name = string.split("_")
        photographer = Photographer.objects.filter(first_name=first_name).filter(last_name=last_name)
        assert len(photographer) == 1
        return photographer[0]

    @staticmethod
    def _get_photographer_string(tags):
        prefix = "photographer/"
        for tag in tags:
            if tag.tag.startswith(prefix):
                return tag.tag[len(prefix):]