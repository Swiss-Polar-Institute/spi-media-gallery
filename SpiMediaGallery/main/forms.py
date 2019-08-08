from django import forms

# from https://stackoverflow.com/questions/17021852/latitude-longitude-widget-for-pointfield/22309195#22309195

from django import forms
from main.models import Medium
from django.contrib.gis.geos import Point


class MediumIdForm(forms.Form):
    medium_id = forms.CharField(label="Photo ID", max_length=255, help_text="Example: SPI-010.jpg, 10, SPI-010.crw")


class LocationEntryCoordinates(forms.ModelForm):
    # This is used in the admin
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
        model = Medium
        exclude = []
        fields = ['file', 'height', 'width', 'duration', 'datetime_taken', 'datetime_imported', 'location',
                       'latitude', 'longitude', 'tags', 'license', 'copyright']

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance'] is not None:
            position = kwargs['instance'].location
        else:
            position = None

        super().__init__(*args, **kwargs)

        if position is not None:
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
