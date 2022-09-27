#!/bin/bash

docker-compose -f docker-compose.dev.yml up -d --build spi-media-gallery

docker-compose -f docker-compose.dev.yml exec spi-media-gallery coverage run manage.py test
