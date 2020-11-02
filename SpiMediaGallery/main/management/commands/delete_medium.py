from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from main.delete_medium import DeleteMedium
from main.models import TagName, Tag, Medium


class Command(BaseCommand):
    help = 'Delete Medium'

    def add_arguments(self, parser):
        parser.add_argument('medium_id', type=str,
                            help='ID of the Medium to delete')

    def handle(self, *args, **options):
        medium_id = options['medium_id']

        try:
            medium = Medium.objects.get(id=medium_id)
        except ObjectDoesNotExist:
            print(f'Medium id {medium_id} does not exist')
            return

        delete_medium = DeleteMedium(medium)
        delete_medium.delete()

        print('Medium deleted')