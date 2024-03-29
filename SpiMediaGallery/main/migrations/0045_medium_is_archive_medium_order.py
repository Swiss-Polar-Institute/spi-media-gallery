# Generated by Django 4.1.2 on 2023-01-13 03:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0044_alter_medium_image_desc"),
    ]

    operations = [
        migrations.AddField(
            model_name="medium",
            name="is_archive",
            field=models.BooleanField(default=False, help_text="is archive"),
        ),
        migrations.AddField(
            model_name="medium",
            name="order",
            field=models.IntegerField(blank=True, help_text="Order", null=True),
        ),
    ]
