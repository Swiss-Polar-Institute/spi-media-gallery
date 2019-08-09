# Generated by Django 2.2.4 on 2019-08-09 11:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_auto_20190809_1101'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='importer',
            field=models.CharField(choices=[('X', 'XMP'), ('G', 'Generated'), ('M', 'Manual')], default='X', max_length=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='file',
            name='bucket',
            field=models.CharField(choices=[('O', 'Original'), ('P', 'Processed')], max_length=1),
        ),
    ]
