from django.core.management.base import BaseCommand

from main.models import Medium, Tag, TagName
from main.progress_report import ProgressReport
from django.core.exceptions import ObjectDoesNotExist
from typing import List


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
            generate_virtual_tags(medium)
            progress_report.increment_and_print_if_needed()


def generate_virtual_tags(medium: Medium):
    for tag in medium.tags.all():
        tag_parts: List[str] = tag.name.name.split("/")

        i = 1
        while i < len(tag_parts):
            new_part = "/".join(tag_parts[0:i])

            try:
                medium.tags.get(name__name=new_part)
                i += 1
                continue
            except ObjectDoesNotExist:
                pass

            try:
                tag_name = TagName.objects.get(name=new_part)
            except ObjectDoesNotExist:
                tag_name = TagName(name=new_part)
                tag_name.save()

            try:
                tag = Tag.objects.get(name=tag_name, importer=Tag.GENERATED)
            except ObjectDoesNotExist:
                tag = Tag()
                tag.name = tag_name
                tag.importer = Tag.GENERATED
                tag.save()

            medium.tags.add(tag)

            i += 1
