#!/bin/bash

if [ ! -n "$1" ]
then
	echo "Please provide directory to export the database to"
	exit 1
fi


if [ ! -d "$1" ]
then
	echo "$1 needs to be a directory"
	exit 1
fi

if [ ! -n "$2" ]
then
	echo "Please provide rclone.conf file (mandatory, to upload the file somewhere)"
	exit 1
fi

if [ ! -n "$3" ]
then
	echo "Please provide the dest:path in rclone"
	exit 1
fi

OUTPUT_DIRECTORY="$1"
RCLONE_CONFIG="$2"
RCLONE_DEST_PATH="$3"

DATETIME="$(date +%Y%m%d-%H%M%S)"

OUTPUT_FILE="$OUTPUT_DIRECTORY/spi-media-gallery-$DATETIME.sql.gz"
docker exec spi-media-gallery_spi-media-gallery_1 mysqldump --defaults-file=/run/secrets/spi_media_gallery_mysql.conf spi_media_gallery | gzip > "$OUTPUT_FILE"
echo "$OUTPUT_FILE"

rclone --config="$RCLONE_CONFIG" copy "$OUTPUT_FILE" "$RCLONE_DEST_PATH"
