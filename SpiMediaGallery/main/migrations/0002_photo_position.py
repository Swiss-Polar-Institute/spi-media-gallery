# Generated by Django 2.2.2 on 2019-06-24 10:21

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='photo',
            name='position',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326),
        ),
    ]
