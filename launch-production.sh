#!/bin/bash

echo "You might need to do: docker build -t spi-media-gallery-docker:0.0.1 ."

echo "docker-compose is not re-building this image"

docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml up --build -d
