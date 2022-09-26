#!/bin/bash

echo "Waiting for mariadb..."

while ! nc -z database 3306; do
  sleep 0.1
done

echo "Mariadb started"

exec "$@"
