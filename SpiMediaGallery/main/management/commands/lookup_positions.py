from django.core.management.base import BaseCommand, CommandError

from main.models import Photo, PhotoResized
from django.conf import settings

from main import spi_s3_utils
from main import utils
from main.progress_report import ProgressReport
from main.datetime_to_position import DatetimeToPosition
from django.contrib.gis.geos import Point


import os

class Command(BaseCommand):
    help = 'Gets date time taken from photos and looks up the position, updates the position'

    def handle(self, *args, **options):
        photos_location_lookup = MediaLocationLookup()

        photos_location_lookup.lookup()


class MediaLocationLookup(object):
    def __init__(self):
        pass

    def lookup(self):
        photos_to_be_lookedup = Photo.objects.filter(location=None).exclude(datetime_taken__isnull=True)

        progress_report = ProgressReport(len(photos_to_be_lookedup), extra_information="Adding location information to photos")

        datetime_to_position = DatetimeToPosition()

        for photo in photos_to_be_lookedup:
            progress_report.increment_and_print_if_needed()

            datetime_taken = photo.datetime_taken

            location = datetime_to_position.lookup_datetime_datetime(datetime_taken)

            if location is None:
                print("No location for this date time")
            else:
                photo.location = Point(location[1], location[0])
                photo.save()
