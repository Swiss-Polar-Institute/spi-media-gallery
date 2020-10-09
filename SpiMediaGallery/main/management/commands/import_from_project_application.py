from django.core.management.base import BaseCommand

from main.importers.project_application_importer import import_resize_update_tags_from_project_application


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('base_url', type=str,
                            help='Hostname to generate the rest or URLs')

    def handle(self, *args, **options):
        hostname = options['base_url']
        bucket_name = 'imported'

        import_resize_update_tags_from_project_application(hostname, bucket_name)
