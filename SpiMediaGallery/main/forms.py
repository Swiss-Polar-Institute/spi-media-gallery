# from https://stackoverflow.com/questions/17021852/latitude-longitude-widget-for-pointfield/22309195#22309195

from django import forms
from django.contrib.gis.geos import Point

from .models import Medium


def media_type_field():
    medium_types = (("A", "Any"),) + Medium.MEDIUM_TYPES
    return forms.ChoiceField(
        choices=medium_types,
        help_text="Result will include only the specific media type",
    )


class MultipleTagsSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        tags = kwargs.pop("tags")
        super().__init__(*args, **kwargs)

        for i, tag in enumerate(tags):
            self.fields[tag["id"]] = forms.BooleanField(
                label="{} ({})".format(tag["tag"], tag["count"]), required=False
            )


class AddReferrerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        referrer = kwargs.pop("referrer")
        super().__init__(*args, **kwargs)

        self.fields[referrer] = forms.CharField(widget=forms.HiddenInput(), initial="1")


class MediaTypeForm(forms.Form):
    media_type = media_type_field()


class MediumIdForm(forms.Form):
    medium_id = forms.CharField(
        label="Media ID",
        max_length=255,
        help_text="Example: SPI-010.jpg, 10, SPI-010.crw",
    )


class FileNameForm(forms.Form):
    filename = forms.CharField(
        label="File name",
        max_length=255,
        help_text="Search for media in which the file path/name contains this text",
    )
    media_type = media_type_field()


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
        fields = (
            "file",
            "medium_type",
            "height",
            "width",
            "duration",
            "datetime_taken",
            "datetime_imported",
            "location",
            "latitude",
            "longitude",
            "tags",
            "photographer",
            "license",
            "copyright",
            "is_image_of_the_week",
        )
        readonly_fields = ("preview",)

    def __init__(self, *args, **kwargs):
        if "instance" in kwargs and kwargs["instance"] is not None:
            position = kwargs["instance"].location
        else:
            position = None

        super().__init__(*args, **kwargs)

        if position is not None:
            self.initial["longitude"], self.initial["latitude"] = position.tuple

    def clean(self):
        # If latitude or longitude fields (not the map) have been changed uses it. Else uses the map.
        point_from_field = None
        if "latitude" in self.changed_data or "longitude" in self.changed_data:
            point_from_field = Point(
                float(self.data["longitude"]), float(self.data["latitude"])
            )

        data = super().clean()

        if point_from_field is not None:
            data["location"] = point_from_field

        return data
