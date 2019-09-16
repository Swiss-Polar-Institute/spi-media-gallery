from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from django.utils import timezone

from ...models import Medium, TagName, Tag, TagRenamed
from ...views import search_for_tag_name_ids

from datetime import datetime


class Command(BaseCommand):
    help = 'Rename tags'

    def add_arguments(self, parser):
        parser.add_argument('old_tag', type=str,
                            help='Tag to be renamed.')
        parser.add_argument('new_tag', type=str,
                            help='New tag name')

    def handle(self, *args, **options):
        old_tag = options['old_tag']
        new_tag = options['new_tag']

        print("Old:", old_tag, "New:", new_tag)

        modifier = ModifyTag()
        modifier.rename(old_tag, new_tag)


class ModifyTag:
    def __init__(self):
        pass


    def _tag_name_is_in_database(self, tag_name_str):
        """Test if tag name is in the database. Return True or False.

        :param tag_name_str: name of the tag
        """

        try:
            TagName.objects.get(name=tag_name_str)
            return True
        except ObjectDoesNotExist:
            return False


    def _get_or_create_tag_in_database(self, tag_name, importer):

        try:
            return Tag.objects.get(name=tag_name, importer=importer)
        except ObjectDoesNotExist:
            new_tag = Tag(name=tag_name, importer=importer)
            new_tag.save()
            return new_tag


    def rename(self, old, new):
        """Check to see if new tag exists. If it exists, abort. If it does not exist, rename the old tag with the new
        name, adding the old / new tag into the TagRenamed model.

        :param old: name of the old tag
        :param new: name of the new tag
        """
        
        # Check if old tag name exists
        if TagName.objects.get(name=old).count() == 0:
            print("Old tag name does not exist: aborting.")
            exit()

        if self._tag_name_is_in_database(new):

            #print('Tag already exists, aborting.')
            tag_name = TagName.objects.get(name=new)
            new_tag = self._get_or_create_tag_in_database(tag_name, Tag.RENAMED)

            # Get list of all media tagged with old tag name
            old_id = TagName.objects.get(name=old).id
            old_media = search_for_tag_name_ids([old_id])[1]
            old_tags = Tag.objects.filter(name__name=old)

            # Tag all of these media with the new tag name, then delete the tags using the old name
            for medium in old_media:
                medium.tags.add(new_tag)
                medium.tags.remove(*old_tags)

            # Delete the old tag from the database
            Tag.objects.filter(name__name=old).delete()
            TagName.objects.get(name=old).delete()

        else:
            tag_name = TagName.objects.get(name=old)
            tag_name.name = new
            tag_name.save()

        renamed_tag = TagRenamed(old_name=old, new_name=new, datetime_renamed=datetime.now(tz=timezone.utc))
        renamed_tag.save()