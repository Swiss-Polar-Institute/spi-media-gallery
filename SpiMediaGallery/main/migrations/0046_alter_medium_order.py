# Generated by Django 4.1.2 on 2023-01-13 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0045_medium_is_archive_medium_order"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medium",
            name="order",
            field=models.IntegerField(
                blank=True, default=1, help_text="Order", null=True
            ),
        ),
    ]
