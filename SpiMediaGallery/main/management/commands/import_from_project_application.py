from django.core.management.base import BaseCommand

from main.importers.project_application_importer import (  # isort:skip
    import_resize_update_tags_from_project_application,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        import_resize_update_tags_from_project_application()
