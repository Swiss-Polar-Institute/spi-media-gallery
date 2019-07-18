#!/bin/bash

python3 manage.py collectstatic --no-input --clear
gunicorn SpiMediaGallery.wsgi:application --bind 0.0.0.0:8000

