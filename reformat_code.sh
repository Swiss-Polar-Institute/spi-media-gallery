#!/bin/bash

docker-compose -f docker-compose.dev.yml up -d --build

docker-compose -f docker-compose.dev.yml exec spi-media-gallery flake8 .
docker-compose -f docker-compose.dev.yml exec spi-media-gallery black --exclude=main/migrations .
docker-compose -f docker-compose.dev.yml exec spi-media-gallery isort --skip=main/migrations .
