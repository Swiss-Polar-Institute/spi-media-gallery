#!/bin/sh

python3 manage collectstatic --no-input --clear
gunicorn SpiMediaGallery.wsgi:application --bind 0.0.0.0:8000

