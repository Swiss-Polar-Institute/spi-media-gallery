from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from ...models import Medium, Tag

from ...progress_report import ProgressReport


class Command(BaseCommand):
    help = 'If a photo is tagged by the same tag name more than once and one of the tags is Manual: untags the manual'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        fix_duplicated_tags = FixDuplicatedTags()
        fix_duplicated_tags.run()


class FixDuplicatedTags:
    def __init__(self):
        pass

    def run(self):
        qs = Medium.objects.all()

        progress_report = ProgressReport(qs.count(), unit='media')

        for medium in qs.all():
            progress_report.increment_and_print_if_needed()

            tags = medium.tags.all()

            for tag in tags:
                if tag.importer == Tag.MANUAL:
                    continue

                try:
                    importer_duplicated = medium.tags.get(name__name=tag.name, importer=Tag.MANUAL)
                except ObjectDoesNotExist:
                    continue

                medium.tags.remove(importer_duplicated)
                print('Untagged: {} from Medium: {}'.format(importer_duplicated, medium))
