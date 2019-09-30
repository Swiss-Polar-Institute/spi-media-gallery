from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from main.models import TagName, Tag


class Command(BaseCommand):
    help = 'Delete tag(s)'

    def add_arguments(self, parser):
        """Define the arguments to be used by the user.

        The command can be run to delete an individual tag.

        TODO: It can also be run to delete tag names that are not used by a medium.
        """

        subparsers = parser.add_subparsers(help='sub-command help', required='True')

        # parser for the command to use an old name and new name
        parser_delete_tag_wrong_name = subparsers.add_parser('name',
                                                                help='Deletes tag because the name is wrong. '
                                                                     'It should not be renamed. NOTE: If you want the '
                                                                     'tag to be renamed instead, please use the command, '
                                                                     'rename_tag')
        parser_delete_tag_wrong_name.set_defaults(dest='name')

        parser_delete_tag_wrong_name.add_argument('tag_name', type=str, help='Tag to be deleted and untagged.')

        # parser for the command to use a set of tags that need to be deleted TODO
        parser_delete_set_tags = subparsers.add_parser('tags', help='deletes a number of tags')
        parser_delete_set_tags.set_defaults(dest='tags')

        parser_delete_set_tags.add_argument('tag_set', type=str, help='set of tags to delete TODO')

    def handle(self, *args, **options):
        if options['dest'] == 'name':
            tag_name = options['tag_name']

            deleter = DeleteTag()
            deleter.delete(tag_name)

            print('The following tag(s) have not been deleted: ')
            print(deleter.tags_not_deleted())

        elif options['dest'] == 'tags':
            pass


class DeleteTag:
    def __init__(self):
        self._tags_not_deleted = []

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

    def _add_tag_to_list_if_does_not_exist(self, tag_name_str):
        """ Check if tag name exists in the database. If it does not, add it to a list (that will be printed at the
        end). If it does, continue.

        :param tag_name_str: tag name (string)
        """

        if TagName.objects.filter(name=tag_name_str).count() == 0:
            self._tags_do_not_exist.append(tag_name_str)
            return True
        else:
            return False


    def tags_not_deleted(self):
        """Returns the list of tags that do not exist in the database and therefore have not been deleted."""

        return self._tags_not_deleted


    def delete(self, tag_name):

        if self._add_tag_to_list_if_does_not_exist(
                tag_name):  # if a tag doesn't exist and it is added to a list, it will return True
            return  # skips the rest of this function (so in effect moves to the next pairing of tags)

        # Delete the  tag from the database
        Tag.objects.filter(name__name=tag_name).delete()
        TagName.objects.get(name=tag_name).delete()
