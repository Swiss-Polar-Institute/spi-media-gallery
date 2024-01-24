#!/bin/bash

docker-compose -f docker-compose.dev.yml up --build -d
docker-compose -f docker-compose.dev.yml exec spi-media-gallery python manage.py migrate
