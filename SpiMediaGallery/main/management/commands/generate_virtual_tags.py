from django.core.management.base import BaseCommand, CommandError

from main.models import Medium, Tag, File
from main.progress_report import ProgressReport
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Generates virtual tags'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        generator = GenerateTags()

        generator.generate_tags()


class GenerateTags(object):
    def __init__(self):
        pass

    def generate_tags(self):
        media = Medium.objects.all()
        progress_report = ProgressReport(len(media), extra_information="Adding virtual tags")

        for medium in media:
            for tag in medium.tags.all():
                tag_parts = tag.tag.split("/")

                i = 1
                while i < len(tag_parts):
                    new_part = "/".join(tag_parts[0:i])

                    try:
                        medium.tags.get(tag=new_part)
                        i += 1
                        continue
                    except ObjectDoesNotExist:
                        pass

                    try:
                        tag = Tag.objects.get(tag=new_part, importer=Tag.GENERATED)
                    except ObjectDoesNotExist:
                        tag = Tag()
                        tag.tag = new_part
                        tag.importer = Tag.GENERATED
                        tag.save()

                    medium.tags.add(tag)

                    i += 1

            progress_report.increment_and_print_if_needed()