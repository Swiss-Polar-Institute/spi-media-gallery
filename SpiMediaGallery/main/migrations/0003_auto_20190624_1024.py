# Generated by Django 2.2.2 on 2019-06-24 10:24

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_photo_position'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='datetime_taken',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='photo',
            name='height',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='photo',
            name='md5',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='photo',
            name='position',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='photo',
            name='width',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
