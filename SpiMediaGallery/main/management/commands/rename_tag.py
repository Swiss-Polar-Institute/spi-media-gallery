from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from django.utils import timezone

from ...models import Medium, TagName, Tag, TagRenamed
from ...views import search_for_tag_name_ids

from datetime import datetime
import csv


class Command(BaseCommand):
    help = 'Rename tags'

    def add_arguments(self, parser):
        """Define the arguments to be used by the user.

        The command can be run using an individual set of old and new tag names, in which case there are two arguments
        required.

        It can also be run using a set of multiple old and new tag names, in which case these are read from a file and
        this is the only argument required.
        """

        # use subparsers because a different number of arguments are required depending on the command used.
        subparsers = parser.add_subparsers(help='sub-command help', required='True')

        # parser for the command to use an old name and new name
        parser_rename_from_command_line = subparsers.add_parser('command_line', help='renames from the command line with an old and new name')
        parser_rename_from_command_line.set_defaults(dest='command_line')

        parser_rename_from_command_line.add_argument('old_tag', type=str, help='Tag to be renamed.')
        parser_rename_from_command_line.add_argument('new_tag', type=str, help='New tag name')

        # parser for the command to use old and new tag names from a csv file
        parser_rename_from_file = subparsers.add_parser('file', help='renames from a file with old and new names')
        parser_rename_from_file.set_defaults(dest='file')

        parser_rename_from_file.add_argument('file_path', type=str, help='Full file path')

    def handle(self, *args, **options):
        if options['dest'] == 'command_line':
            old_tag = options['old_tag']
            new_tag = options['new_tag']

            modifier = ModifyTag()
            modifier.rename(old_tag, new_tag)

        elif options['dest'] == 'file':
            modifier = ModifyTag()
            file_path = options['file_path']
            modifier.rename_from_file(file_path)


class ModifyTag:
    def __init__(self):
        pass

    def rename_from_file(self, file_path):
        """Get the old and new tag names from a file.

        :param file_path: full path to the file containing the old and new tag names"""

        with open(file_path) as csvfile:
            tag_row = csv.reader(csvfile)

            for tags in tag_row:

                old_tag = tags[0]
                new_tag = tags[1]

                print('Renaming: ', old_tag, ' to ', new_tag)
                self.rename(old_tag, new_tag)


    @staticmethod
    def _tag_name_is_in_database(self, tag_name_str):
        """Test if tag name is in the database. Return True or False.

        :param tag_name_str: name of the tag
        """

        try:
            TagName.objects.get(name=tag_name_str)
            return True
        except ObjectDoesNotExist:
            return False

    @staticmethod
    def _get_or_create_tag_in_database(tag_name, importer):
        """Get the tag object from the database if it already exists, then return it. If not, create the tag and return it.

        :param tag_name: tag_name object
        :param importer: importer method used when adding the tag to the database
        """

        try:
            return Tag.objects.get(name=tag_name, importer=importer)
        except ObjectDoesNotExist:
            new_tag = Tag(name=tag_name, importer=importer)
            new_tag.save()
            return new_tag

    @staticmethod
    def _raise_error_if_old_tag_does_not_exist(old):
        """ Check if old tag name exists in the database. If it does not, raise command error. If it does, continue.

        :param old: old tag name (string)
        """

        if TagName.objects.filter(name=old).count() == 0:
            raise CommandError('Old tag {} name does not exist: aborting.'.format(old))

    @staticmethod
    def _raise_error_if_old_tag_same_as_new(old, new):
        """Check if the old and new tags are the same. If they are, abort.

        :param old: old tag name (string)
        :param new: new tag name (string)"""

        if old == new:
            raise CommandError('Old tag is the same as the new tag: aborting.')

    def rename(self, old, new):
        """Check to see if new tag exists. If it exists, abort. If it does not exist, rename the old tag with the new
        name, adding the old / new tag into the TagRenamed model.

        :param old: name of the old tag
        :param new: name of the new tag
        """

        self._raise_error_if_old_tag_same_as_new(old, new)

        self._raise_error_if_old_tag_does_not_exist(old)

        if self._tag_name_is_in_database(self, new):

            tag_name = TagName.objects.get(name=new)
            new_tag = ModifyTag._get_or_create_tag_in_database(tag_name, Tag.RENAMED)

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
            # Rename the tag with the new name
            tag_name = TagName.objects.get(name=old)
            tag_name.name = new
            tag_name.save()

        # Add a row to the TagRenamed table to record each change or renaming of tags. This includes tags that are
        # renamed, or those that are changed to be ones that already exist in the database.
        renamed_tag = TagRenamed(old_name=old, new_name=new, datetime_renamed=datetime.now(tz=timezone.utc))
        renamed_tag.save()