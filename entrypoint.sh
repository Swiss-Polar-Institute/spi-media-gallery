#!/bin/bash

python3 manage.py migrate
python3 manage.py collectstatic --no-input --clear

mkdir -p /srv/logs
touch /srv/logs/gunicorn.log
touch /srv/logs/access.log
tail -n 0 -f /srv/logs/*.log &

gunicorn SpiMediaGallery.wsgi:application \
	--bind 0.0.0.0:8000 \
	--workers 20 \
	--log-level=info \
	--log-file=/srv/logs/gunicorn.log \
	--timeout=7200 \
	--access-logfile=/srv/logs/access.log
	"$@"

