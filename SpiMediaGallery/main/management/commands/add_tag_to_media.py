from django.core.management.base import BaseCommand

from ...models import Medium, Tag, TagName


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

        assign_tag_from_command_line.add_argument('object_storage_key', type=str, help='Regular expression of object storage key')
        assign_tag_from_command_line.add_argument('tagname', type=str, help='Tag name to assign')
        assign_tag_from_command_line.add_argument('--dry-run', action='store_true')

        assign_tag_from_file = subparsers.add_parser('file', help='adds tags from list in a file')
        assign_tag_from_file.set_defaults(dest='file')

        assign_tag_from_file.add_argument('file_path', type=str,
                                          help='Full file path of file containing media and tags to be assigned')

    def handle(self, *args, **options):
        if options['dest'] == 'command_line':
            object_storage_key = options['object_storage_key']
            tagname = options['tagname']
            dry_run = options['dry_run']

            assigner = AssignTag()
            assigner.add_tag(object_storage_key, tagname, dry_run)

        elif options['dest'] == 'file':
            assigner = AssignTag()
            file_path = options['file_path']
            assigner.add_tag_from_file(file_path)


class AssignTag():
    def __init__(self):
        pass

    def add_tag(self, object_storage_key, tagname_str, dry_run):
        """Assign the tag with tagname to the media with the defined object storage key."""

        # Get or create tag
        tagname, created = TagName.objects.get_or_create(
            name=tagname_str
        )

        tag, created = Tag.objects.get_or_create(
            name=tagname,
            importer=Tag.MANUAL
        )

        # Check that object storage key exists

        total_number_media = 0
        total_number_media_modified = 0

        # Add the tag to the medium
        for medium in Medium.objects.filter(file__object_storage_key=object_storage_key):

            number_tags_before_adding_tag = medium.tags.all().count()

            if dry_run:
                print(medium.file.object_storage_key)
            else:
                medium.tags.add(tag)

                if medium.tags.all().count() != number_tags_before_adding_tag:
                    total_number_media_modified += 1

            total_number_media += 1

        print('Total number media queried:', total_number_media)
        print('Total number media to which tags were added:', total_number_media_modified)
