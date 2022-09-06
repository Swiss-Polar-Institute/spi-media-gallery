#!/bin/bash

docker-compose -f docker-compose.dev.yml up -d --build

docker-compose -f docker-compose.dev.yml exec spi-media-gallery coverage run manage.py test
