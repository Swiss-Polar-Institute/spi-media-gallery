# Generated by Django 2.2.2 on 2019-07-27 06:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_auto_20190727_0635'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mediumresized',
            name='height',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='mediumresized',
            name='width',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
