# Generated by Django 2.2.2 on 2019-07-23 09:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_media_media_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mediaresized',
            old_name='photo',
            new_name='media',
        ),
    ]
