from django.core.management.base import BaseCommand

from ...models import Medium, Photographer
from ...progress_report import ProgressReport


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
        photos_without_photographer_count = photos_without_photographer.count()

        progress_report = ProgressReport(photos_without_photographer_count,
                                         extra_information='Updating photographer of photos')

        invalid_photographers = set()

        for photo in photos_without_photographer:
            progress_report.increment_and_print_if_needed()

            photographer_str = self._get_photographer_string(photo.tags.all())

            if photographer_str is None:
                print('Photo without photographer tag:', photo.file.object_storage_key)
                continue

            photographer = self._get_photographer(photographer_str)

            if photographer is None:
                invalid_photographers.add(photographer_str)
            else:
                photo.photographer = photographer
                photo.save()

        print('Invalid photographers: {}'.format(invalid_photographers))

    @staticmethod
    def _get_photographer(string):
        if string.count('_') != 1:
            print('Invalid photographer tag format: {}'.format(string))
            return None

        first_name, last_name = string.split('_')
        photographer = Photographer.objects.filter(first_name=first_name).filter(last_name=last_name)

        if len(photographer) == 1:
            return photographer[0]
        elif len(photographer) > 1:
            print('More than one photographer in the DB for {}'.format(string))
        elif len(photographer) == 0:
            print('Photographer cannot be found in the database: {}'.format(string))

        return None

    @staticmethod
    def _get_photographer_string(tags):
        prefix = 'photographer/'
        for tag in tags:
            if tag.name.name.startswith(prefix):
                return tag.name.name[len(prefix):]
