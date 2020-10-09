# Generated by Django 3.1.2 on 2020-10-09 08:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0038_add_spdx_license_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='remotemedium',
            name='api_source',
            field=models.CharField(choices=[('PROJECT_APPLICATION', 'Project Application')], default='PROJECT_APPLICATION', help_text='Which API this photos was fetched from', max_length=20),
        ),
    ]