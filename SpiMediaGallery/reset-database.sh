#!/bin/bash

echo "drop database spi_media_gallery; create database spi_media_gallery;" | python3 manage.py dbshell

#rm -rf main/migrations/

#echo "Make migrations"
#python3 manage.py makemigrations main

echo "Migrate:"
python3 manage.py migrate

echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin')" | python manage.py shell
