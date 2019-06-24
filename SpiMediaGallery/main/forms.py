from django import forms

# from https://stackoverflow.com/questions/17021852/latitude-longitude-widget-for-pointfield/22309195#22309195

from django import forms
from main.models import Photo
from django.contrib.gis.geos import Point


class LocationEntryCoordinates(forms.ModelForm):
    latitude = forms.FloatField(
        min_value=-90,
        max_value=90,
        required=False,
    )
    longitude = forms.FloatField(
        min_value=-180,
        max_value=180,
        required=False,
    )

    class Meta(object):
        model = Photo
        exclude = []
        fields = ['object_storage_key', 'md5', 'file_size', 'height', 'width', 'datetime_taken', 'location',
                       'latitude', 'longitude']

    def __init__(self, *args, **kwargs):
        position = kwargs['instance'].location

        super().__init__(*args, **kwargs)

        self.initial['longitude'], self.initial['latitude'] = position.tuple

    def clean(self):
        # If latitude or longitude fields (not the map) have been changed uses it. Else uses the map.
        point_from_field = None
        if 'latitude' in self.changed_data or 'longitude' in self.changed_data:
            point_from_field = Point(float(self.data['longitude']), float(self.data['latitude']))

        data = super().clean()

        if point_from_field is not None:
            data['location'] = point_from_field

        return data