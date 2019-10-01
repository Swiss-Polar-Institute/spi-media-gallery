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

        # Get the media that do not have a photographer linked to them
        photos_without_photographer = Medium.objects.filter(photographer__isnull=True)

        # Count the number of media without a photographer link
        photos_without_photographer_count = photos_without_photographer.count()

        progress_report = ProgressReport(photos_without_photographer_count,
                                         extra_information='Updating photographer of photos')

        invalid_photographers = set()

        # For the media that are not linked with a photographer, try and find a matching photographer
        for photo in photos_without_photographer:
            progress_report.increment_and_print_if_needed()

            # Get the name of the photographer from the tag that has been applied
            photographer_str = self._get_photographer_string(photo.tags.all())

            # If the medium has not been tagged with a photographer, then continue with the next medium
            if photographer_str is None:
                print('Photo without photographer tag:', photo.file.object_storage_key)
                continue

            # Get the photographer name for those that are tagged with a photographer
            photographer = self._get_photographer(photographer_str)

            if photographer is None: # if the photographer cannot be found in the database, then add them to an output list of invalid photographers
                invalid_photographers.add(photographer_str)
            else: # if the name is found in the database table then link this medium with the photographer
                photo.photographer = photographer
                photo.save()

        print('Invalid photographers: {}'.format(invalid_photographers))

    @staticmethod
    def _get_photographer(string):
        # if string.count(' ') != 1: # name is expected in the format name_surname where a space joins two names together for example john_doe brown
        #     print('Invalid photographer tag format: {}'.format(string))
        #     return None

        # create the name of the photographer from the tag name and find the correct photographer in the database
        first_name, last_name = string.split(' ', 1)
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
        prefix = 'Photographer/'
        for tag in tags:
            if tag.name.name.startswith(prefix):
                return tag.name.name[len(prefix):]
