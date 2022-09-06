#!/bin/bash

echo "Waiting for mariadb..."

while ! nc -z database 3306; do
  sleep 0.1
done

echo "Mariadb started"

python manage.py migrate
python manage.py collectstatic --no-input --clear
python manage.py runserver 0.0.0.0:8000
