from django.core.management.base import BaseCommand

from ...models import Medium, TagName

import re


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

        for tag_name in TagName.objects.filter(name__startswith=old_tag):
            tag_name.name = re.sub('^' + old_tag, new_tag, tag_name.name)
            tag_name.save()

        TagName.objects.filter(name=old_tag).update(name=new_tag)