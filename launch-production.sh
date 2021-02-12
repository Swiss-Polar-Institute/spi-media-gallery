#!/bin/bash

echo "You might need to do: ./docker-build.sh"

docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml up --build -d
