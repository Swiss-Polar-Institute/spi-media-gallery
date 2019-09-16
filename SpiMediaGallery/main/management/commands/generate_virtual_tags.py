from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from ...models import Medium, Tag, TagName
from ...progress_report import ProgressReport


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
    """For each tag of :param medium checks that the parent tag exists. If it does not exist creates it
    with the tag.type == Tag.GENERATED. E.g. if "people/john_doe" is a tag in :param medium creates
    "people" (type is generated)
    """
    for tag in medium.tags.all():
        tag_parts: List[str] = tag.name.name.split('/')

        i = 1
        while i < len(tag_parts):
            new_part = "/".join(tag_parts[0:i])

            try:
                medium.tags.get(name__name=new_part)
                i += 1
                # A tag already exists, nothing to do
                continue
            except ObjectDoesNotExist:
                pass

            # Checks if TagName exists or creates it
            try:
                tag_name = TagName.objects.get(name=new_part)
            except ObjectDoesNotExist:
                tag_name = TagName(name=new_part)
                tag_name.save()

            # Creates Tag (with tag_name, generated) or finds it
            try:
                tag = Tag.objects.get(name=tag_name, importer=Tag.GENERATED)
            except ObjectDoesNotExist:
                tag = Tag()
                tag.name = tag_name
                tag.importer = Tag.GENERATED
                tag.save()

            medium.tags.add(tag)

            i += 1
