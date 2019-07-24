# Generated by Django 2.2.2 on 2019-07-02 13:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_auto_20190702_1033'),
    ]

    operations = [
        migrations.CreateModel(
            name='Copyright',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('holder', models.CharField(max_length=255)),
                ('public_text', models.TextField(help_text='Text displayed to the user for the copyright holder')),
            ],
        ),
    ]
