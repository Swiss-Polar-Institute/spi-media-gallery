# Generated by Django 2.2.2 on 2019-07-24 09:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_media_duration'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Media',
            new_name='Medium',
        ),
        migrations.RenameModel(
            old_name='MediaResized',
            new_name='MediumResized',
        ),
        migrations.RenameField(
            model_name='medium',
            old_name='media_type',
            new_name='medium_type',
        ),
    ]
