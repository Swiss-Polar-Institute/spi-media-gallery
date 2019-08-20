import sqlite3

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Reads sqlite3 file with the positions and generates a GeoJSON file'

    def add_arguments(self, parser):
        parser.add_argument('sqlite3file', type=str,
                            help="Needs to have a table named `gps` with at least the fields `date_time`, `latitude` and `longitude`")
        parser.add_argument('output_file', type=str, help="New GeoJSON file")

    def handle(self, *args, **options):
        sqlite3_filepath = options["sqlite3file"]
        output_filepath = options["output_file"]

        generator = Sqlite3toGeojson(sqlite3_filepath, output_filepath)

        generator.generate()


class Sqlite3toGeojson(object):
    def __init__(self, sqlite3_filepath, output_filepath):
        self._output_filepath = output_filepath

        self._sqlite3_connection = sqlite3.connect(sqlite3_filepath)
        self._cursor = self._sqlite3_connection.cursor()

    def generate(self):
        self._cursor.execute("SELECT latitude, longitude FROM gps WHERE date_time LIKE '%:00:00%'")

        multi_line_string = MultiLineString()

        previous_point = None
        locations = []

        for row in self._cursor:
            current_point = Point(float(row[1]), float(row[0]))

            if previous_point is not None:
                distance = current_point.distance(previous_point)

                if distance > 10:  # units: degrees
                    if len(locations) > 1:
                        multi_line_string.append(LineString(locations))
                    locations = []

            locations.append((float(row[1]), float(row[0])))
            previous_point = current_point

        if len(locations) > 1:
            multi_line_string.append(LineString(locations))

        with open(self._output_filepath, "w") as f:
            f.write(multi_line_string.geojson)

        print("Result saved in {}".format(self._output_filepath))
