# Generated by Django 2.2.2 on 2019-07-24 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_auto_20190724_1503'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='medium',
            options={'verbose_name_plural': 'Media'},
        ),
        migrations.AlterModelOptions(
            name='mediumresized',
            options={'verbose_name_plural': 'MediaResized'},
        ),
        migrations.AlterField(
            model_name='medium',
            name='file_size',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='mediumresized',
            name='file_size',
            field=models.BigIntegerField(),
        ),
    ]
