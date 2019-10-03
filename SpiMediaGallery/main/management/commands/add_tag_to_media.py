from django.core.management.base import BaseCommand

from ...models import Medium, Tag, TagName
import csv


class Command(BaseCommand):
    help = 'Assign tags to media.'

    def add_arguments(self, parser):
        """Define the commands to be used by the user.

        The command can be used using an object storage key (file path) and tag name on the command line. Give the option of dry-run to check media that would be modified.

        It can also be used with a file containing a list of the media to which the tags can be assigned.
        """
        subparsers = parser.add_subparsers(help='sub-command help', required='True')

        assign_tag_from_command_line = subparsers.add_parser('command_line',
                                                             help='adds tag from command line using the object storage key and tag name')
        assign_tag_from_command_line.set_defaults(dest='command_line')

        assign_tag_from_command_line.add_argument('object_storage_key_regex', type=str, help='Regular expression of object storage key')
        assign_tag_from_command_line.add_argument('tagname', type=str, help='Tag name to assign')
        assign_tag_from_command_line.add_argument('--dry-run', action='store_true')

        assign_tag_from_file = subparsers.add_parser('file', help='adds tags from list in a file')
        assign_tag_from_file.set_defaults(dest='file')

        assign_tag_from_file.add_argument('file_path', type=str,
                                          help='Full file path of file containing media and tags to be assigned')
        assign_tag_from_file.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        assigner = AssignTag()

        if options['dest'] == 'command_line':
            object_storage_key_regex = options['object_storage_key_regex']
            tagname = options['tagname']
            dry_run = options['dry_run']

            assigner.add_tag(object_storage_key_regex, tagname, dry_run)

        elif options['dest'] == 'file':
            file_path = options['file_path']
            dry_run = options['dry_run']
            assigner.add_tag_from_file(file_path, dry_run)

            print('Total number of media', assigner.total_number_media)
            print('Total number of media modified', assigner.total_number_media_modified)


class AssignTag():
    def __init__(self):
        self.total_number_media = 0
        self.total_number_media_modified = 0

    def add_tag(self, object_storage_key_regex, tagname_str, dry_run):
        """Assign the tag with tagname to the media with the defined object storage key."""

        # Get or create tag
        tagname, created = TagName.objects.get_or_create(
            name=tagname_str
        )

        tag, created = Tag.objects.get_or_create(
            name=tagname,
            importer=Tag.MANUAL
        )

        total_number_media_tag = 0
        total_number_media_tag_modified = 0

        # Add the tag to the medium
        for medium in Medium.objects.filter(file__object_storage_key__iregex=object_storage_key_regex):

            number_tags_before_adding_tag = medium.tags.all().count()

            if dry_run:
                print(medium.file.object_storage_key)
            else:
                medium.tags.add(tag)

                if medium.tags.all().count() != number_tags_before_adding_tag:
                    total_number_media_tag_modified += 1

            total_number_media_tag += 1

        self.total_number_media_modified += total_number_media_tag_modified
        self.total_number_media += total_number_media_tag

        print('Total number of media for this object storage key and tag', total_number_media_tag)
        print('Total number of media modified for this object storage key and tag', total_number_media_tag_modified)

    def add_tag_from_file(self, file_path, dry_run):
        """Add tag to media that are listed in a csv file with a regular expression for the object storage and a tag name"""

        with open(file_path) as csvfile:
            object_storage_to_tag = csv.reader(csvfile)

            for rows in object_storage_to_tag:
                object_storage_key_regex = rows[0]
                tagname_str = rows[1]

                print("-----Adding tags to media that have an object storage key that meets the following expression:", object_storage_key_regex, "-----")
                self.add_tag(object_storage_key_regex, tagname_str, dry_run)
