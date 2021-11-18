from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from main.delete_medium import DeleteMedium
from main.models import Medium, File


class Command(BaseCommand):
    help = 'Delete Medium'

    def add_arguments(self, parser):
        parser.add_argument('--medium_id', type=int,
                            help='ID of the Medium to delete')
        parser.add_argument('--medium_file_path', type=str,
                            help='File path of the file to delete')

    def handle(self, *args, **options):
        if 'medium_id' in options:
            medium_id = options['medium_id']
            try:
                medium = Medium.objects.get(id=medium_id)
            except ObjectDoesNotExist:
                print(f'Medium id {medium_id} does not exist')
                return

        elif 'medium_file_path' in options:
            medium_file_path = options['medium_file_path']
            try:
                medium = Medium.objects.get(file__object_storage_key=medium_file_path)
            except ObjectDoesNotExist:
                print(f'Medium path {medium_file_path} does not exist')
                return
            except Medium.MultipleObjectsReturned:
                print(f'More than one medium has {medium_file_path} file path')
                return
        else:
            print('Please use --medium_id or --medium_file_path options')
            return

        delete_medium = DeleteMedium(medium)
        delete_medium.delete()

        print(f'Medium deleted: {medium.id}')
