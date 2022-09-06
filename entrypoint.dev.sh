#!/bin/bash

echo "Waiting for mariadb..."

while ! nc -z database 3306; do
  sleep 0.1
done

echo "Mariadb started"

python3 manage.py migrate
python3 manage.py collectstatic --no-input --clear
python3 manage.py runserver 0.0.0.0:8000
