from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import ProtectedError

from ...models import Medium, Tag, TagName
from ...progress_report import ProgressReport


class Command(BaseCommand):
    help = 'Generates virtual tags'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        generator = GenerateTags()

        generator.delete_generated_tags()
        generator.generate_tags()


class GenerateTags(object):
    def __init__(self):
        pass

    def delete_generated_tags(self):
        """Delete all generated tags (before the new ones are generated to avoid them becoming orphan tags when renaming
            is done). """

        for tag in Tag.objects.filter(importer=Tag.GENERATED):
            tagname = tag.name  # gets the associated tag name
            tag.delete()  # deleted tag from Tag

            try:
                tagname.delete()  # deletes tagname from Tagname where is was GENERATED but only if there isn't another tag in Tag with this same name
            except ProtectedError:  # catches the error to stop the delete of the Tagname if there is another tag with this name but with a different importer
                pass

    def generate_tags(self):
        media = Medium.objects.all()
        progress_report = ProgressReport(len(media), extra_information="Adding virtual tags")

        for medium in media:
            generate_virtual_tags_from_medium(medium)
            progress_report.increment_and_print_if_needed()

    def delete_tags_if_orphaned(self, tags_to_maybe_delete):
        for tag in tags_to_maybe_delete:
            if tag.medium_set.count() == 0:
                tag_name = tag.name

                tag.delete()

                if tag_name.tag_set.count() == 0:
                    # Used only by the one that we are deleting
                    tag_name.delete()

    def generate_tags_for_medium(self, medium):
        generate_virtual_tags_from_medium(medium)


def generate_virtual_tags_from_medium(medium: Medium):
    """For each tag of :param medium it checks that the parent tag exists. If it does not exist it creates it
    with the tag.type == Tag.GENERATED. E.g. if "people/john_doe" is a tag in :param medium it creates
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
