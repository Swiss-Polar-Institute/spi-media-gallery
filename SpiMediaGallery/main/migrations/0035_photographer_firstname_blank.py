# Generated by Django 2.2.4 on 2019-10-02 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0034_photographer_firstname_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photographer',
            name='first_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
