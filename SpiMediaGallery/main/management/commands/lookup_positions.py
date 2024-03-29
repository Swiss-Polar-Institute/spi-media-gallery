from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from ...datetime_to_position import DatetimeToPosition
from ...models import Medium
from ...progress_report import ProgressReport


class Command(BaseCommand):
    help = "Gets date time taken from photos and looks up the position, updates the position"

    def handle(self, *args, **options):
        photos_location_lookup = MediaLocationLookup()

        photos_location_lookup.lookup()


class MediaLocationLookup(object):
    def __init__(self):
        pass

    def lookup(self):
        media_to_geolocate = Medium.objects.filter(location=None).exclude(
            datetime_taken__isnull=True
        )

        progress_report = ProgressReport(
            media_to_geolocate.count(),
            extra_information="Adding location information to media",
        )

        datetime_to_position = DatetimeToPosition()

        for photo in media_to_geolocate:
            progress_report.increment_and_print_if_needed()

            datetime_taken = photo.datetime_taken

            location = datetime_to_position.lookup_datetime_datetime(datetime_taken)

            if location is None:
                print("No location for: {}".format(datetime_taken))
            else:
                photo.location = Point(location[1], location[0])
                photo.save()
