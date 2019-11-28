# spi-media-gallery

spi-media-gallery is a Django application developed for SPI, currently used internally.

SPI has media stored in an object storage bucket (it's a in-house bucket but it could be an S3 bucket). It has more than 45000 photos (JPEG and different raw formats, about 0.5 TB) and more than 5000 videos (about 3.5 TB).

This tool was developed to be able to give easy access to these files. Different features of the tool:
 * It has support to create different sizes of the media in JPEG or webm (so any user with just a browser can access them)
 * It can import tags from Digikam XMP files into the database
 * It extracts the date+time of the photos, it can read a GPS track and geo-locate the photos (or manually)
 * Can search by tag or intersection of tags
 * Tags has a hierarchy
 * Can provide a list of all the videos or a CSV to make them easy to review
 * Can associate a photographer and a license to each photo
 * Django commands in order to associate photographers, copyright and licenses (based on the path of photos)
 * It has Django commands in order to rename tags or "merge" tags
 * It can export a directory as thumbnails and XMP files with the tags (not used much)
 
The tool could be used by other projects with similar needs (organise huge amount of photos). The advantage of this tool with other possible tools is that it's relatively easy to tune for specific needs. Ask if you doubt how to do something. The disavadvantage is obviously that it has been used only by one project and some features should be moved into the settings in order to personalise them better.

Currently, in order to add new media, it's needed to use Django commands: it's not possible to add media using or the web interface.

First part of the homepage:

<img src="documentation/images/media-gallery-homepage-01.png" width="500">

Tags with hierarchy:

<img src="documentation/images/media-gallery-homepage-02.png" width="500">

Second part of the homepage:

<img src="documentation/images/media-gallery-homepage-03.png" width="500">

Section to select multiple tags and see media with those tags:

<img src="documentation/images/media-gallery-multiple-tags-01.png" width="500">

Photos intersection of two tags:

<img src="documentation/images/media-gallery-thumbnails-01.png" width="500">

Example of a photo:
<img src="documentation/images/media-gallery-photo-01.png" width="500">
