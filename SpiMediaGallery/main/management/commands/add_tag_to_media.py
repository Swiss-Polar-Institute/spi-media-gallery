from django.core.management.base import BaseCommand

from ...models import Medium

class Command(BaseCommand):
    help = 'Assign tags to media.'

    def add_arguments(self, parser):
        """Define the commands to be used by the user.

        The command can be used using an object storage key (file path) and tag name on the command line.

        It can also be used with a file containing a list of the media to which the tags can be assigned.
        """
        subparsers = parser.add_subparsers(help='sub-command help', required='True')

        assign_tag_from_command_line = subparsers.add_parser('command_line', help='adds tag from command line using the object storage key and tag name')
        assign_tag_from_command_line.set_defaults(dest='command_line')

        assign_tag_from_command_line.add_argument('object_storage_key', type=str, help='Regular expression of object storage key')
        assign_tag_from_command_line.add_argument('tagname', type=str, help='Tag name to assign')

        assign_tag_from_file = subparsers.add_parser('file', help='adds tags from list in a file')
        assign_tag_from_file.set_defaults(dest='file')

        assign_tag_from_file.add_argument('file_path', type=str, help='Full file path of file containing media and tags to be assigned')

    def handle(self, *args, **options):
        if options['dest'] == 'command_line':
            object_storage_key = options['object_storage_key']
            tagname = options['tagname']

            assigner = AssignTag()
            assigner.add_tag(object_storage_key, tagname)

        elif options['dest'] == 'file':
            assigner = AssignTag()
            file_path = options['file_path']
            assigner.add_tag_from_file(file_path)


class AssignTag():
    def __init__(self):
        pass
    
