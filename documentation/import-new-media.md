# Import new media
This documentation is written but not "tested" (not written while doing an import) so
there might be mistakes. Probably the source code is a good place to clarify things that
don't quite work.

## Copy media into the bucket "original"
In SPI this bucket is referenced by `~/config/spi_media_gallery_buckets.json` named "spi-media-raw" (see the `settings.py` to see it in your instance.

This can be done from a hard disk, another storage, etc. using `rclone` or your favourite way
to manage object storage files. The media gallery doesn't have a way to upload
files there. Copy the *.xmp files as well (used later one for the tags)

Actually the SPI media gallery has read only access to the "spi-media-raw" bucket
so oit wouldn't be able to add files. The SPI Media Gallery has another bucket named
"imported" for media that came from an API (this is not fully implemented).

## Add files and tags from the bucket into the database
Using the django command: `add_files_with_tags --prefix prefix_with_the_new_media_in_object_storage/` will find the new media and add
it into the database. It will also read the XMP files (searching the XMP file as
name_of_the_media.jpg.xmp) and read and associate the tags.

Note: before adding the tags it might be useful to normalise them with
existing tags (penguin VS penguins)  

## Resize the media
The raw media, imported, might be in different file formats (JPEG, RAW files,
different video formats, etc.) and these are not usable by the browsers or might
be too big to be used as thumbnails in some of the pages.

You can resize the media using the Django command:
`resize_media`. For example:

`resize_media Photos T S M L O` (it might need to be TSMLO?)
`resize_media Videos T`

Where T S M L O stands for Thumbnail, Small, Medium, Large and Original size.

Please refer to IMAGE_LABEL_TO_SIZES in settings.py to see the sizes in your installation.

Besides, resizing the media it will also store it as JPEG or webm.

The process uses ffmpeg and imagemagick. It doesn't use PIL Python package because
when we tried to use it for some images and formats it didn't work correctly.

Side note: See Dockerfile for some changes in /etc/ImageMagick-6/policy.xml to allow
ImageMagick work with bigger (panoramic) photos.

Important note: resizing the photos and media takes time. For the Antarctica Circumnavigation
Expedition media if I remember correctly it took between 4 and 6 weeks. We resized the 
videos only to one resolution (Thumbnail) to avoid another 4 weeks of processing.

The photos are usually faster.

Note: it might be useful to do the resizing in a separate server(s) to avoid
higher load average in the production server.

## generate_virtual_tags

Probably the XMP files will have tags like `wildlife/birds/penguins` (or similar).

The Django command `add_files_with_tags` will add the tag `wildlife/birds/penguins`
to the photo. But in order to make this photo accessible via `wildlife/birds` or `wildlife`
it's needed to create virtual tags. This is done with the Django command `generate_virtual_tags`.

The command `generate_virtual_tags` don't have any parameters.

## Add photographer

The tags should have the photographer tag. To update the photographer field
it's needed to use `update_photographers`. It reads the photographer of the
tags and sets the photographer field.

## Add license
Each medium has a license associated. While I'm writing the documentation
I cannot find any command that I might have used to set the licenses.

I think that I might have used the database via Django shell to attach the
licenses based on the prefix of the medium.

## Update date time taken
Use the Django command `update_datetime_taken` and
`update_datetime_taken_videos` reads the date time taken of the media
and sets it into the database.

This is useful to display it to the user when browsing media and also
for the setup "Lookup the coordinates of the images".


## Fix tags
We created some Django commands to fix possible problems:
 * `delete_tag`: deletes a tag
 * `rename_tag`: renames  a tag
 * `add_tag_to_media`
 * `fix_duplicate_manual_tag`

There might be other cases that is needed to deal with the database
straight away.

## Lookup the coordinates of the images

The step "Update datetime taken" reads the date time of the image and saves it
into the database.

SPI Media Gallery also has the latitude-longitude of the photos. This is useful
to display the place of the photo in a small map on each media and also to find
media that were taken in a similar location.

In the SPI Media Gallery instance from SPI for the Antarctica Circumnavigation
Expedition photos (2016-2017): we made the cruise track available to the SPI
Media Gallery. Following to this the command `lookup_positions` was used
to lookup the lat-long based on the datetime of certain media.

In order to do this a .sqlite3 database is made available (see
DATETIME_POSITIONS_SQLITE3_PATH in settings.py) and media the command
`lookup_positions` finds the media without a lat-long and uses the file
to import the lat-long.

For the Arctic Century media, the .sqlite3 database
with the required columns will need to be created. The source of
information can be the Zenodo cruise track (in CSV, need to be imported
into .sqlite3 for the SPI Media Gallery to use it).

## Check the integrity
The Django command `check_integrity` checks the integrity between the database,
object storage and also tags.

The main goal of `check_integrity` is to report orphaned tags, orphaned media
(media that exist in the database but not in the object storage or the other way
round).

It only informs of the problem but it doesn't take any actions. You will need to
address any possible problems.

# What is "imported" bucket?

The imported bucket is a bucket that the media gallery has read/write access
and is used by a small API that we started building. Nestor (project-application)
is able to push new media into the SPI Media Gallery and this media get
copied into the imported.

This project wasn't finished and the "imported" bucket is not actively used
by SPI at the moment.

# What is export_media command?

There was a need to create a directory with certain photos to send it to someone.
We created this command to export some photos easier.
