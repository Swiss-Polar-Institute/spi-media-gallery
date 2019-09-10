from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from django.utils import timezone

from ...models import Medium, TagName, Tag, TagRenamed

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
        #
        # for tag_name in TagName.objects.filter(name__startswith=old_tag):
        #     tag_name.name = re.sub('^' + old_tag, new_tag, tag_name.name)
        #     tag_name.save()
        #
        # TagName.objects.filter(name=old_tag).update(name=new_tag)

class ModifyTag:
    def __init__(self):
        pass


    def tag_name_is_in_database(self, tag):
        try:
            TagName.objects.get(name=tag)
            return True
        except ObjectDoesNotExist:
            return False


    def rename(self, old, new):

        if self.tag_name_is_in_database(new):
            '''Check to see if new tag exists. If it exists, abort.'''
            print('Tag already exists, aborting.')
        else:
            '''If it does not exist, rename the old tag with the new name.'''
            tag_name = TagName.objects.get(name=old)
            tag_name.name = new
            tag_name.save()

            '''Add the old / new tag into the TagRenamed model.'''
            renamed_tag = TagRenamed(old_name=old, new_name=new, datetime_renamed=datetime.now(tz=timezone.utc))
            renamed_tag.save()