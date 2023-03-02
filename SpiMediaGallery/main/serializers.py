from django.utils import timezone
from rest_framework import serializers

from .medium_for_view import MediumForView
from .models import Copyright, File, License, Medium, Photographer, Tag
from .utils import set_tags


class TageSerializer(serializers.ModelSerializer):
    importer = serializers.CharField(default="M")
    name = serializers.CharField(source="name.name")

    class Meta:
        model = Tag
        fields = "__all__"


class MediumSerializer(serializers.ModelSerializer):
    tags = TageSerializer(required=False, many=True, read_only=True)
    datetime_imported = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = Medium
        fields = "__all__"

    def create(self, validated_data):
        medium = Medium.objects.create(**validated_data)
        tags_name = [
            self.initial_data[tag] for tag in self.initial_data if tag.startswith("tag")
        ]
        for tag in tags_name:
            set_tags(medium, tag, "M")
        return medium


class PhotographerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photographer
        fields = "__all__"


class CopyrightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Copyright
        fields = "__all__"


class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = "__all__"


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"


class MediumDataSerializer(serializers.ModelSerializer):
    tags = TageSerializer(required=False, many=True)
    copyright = CopyrightSerializer(required=False, read_only=True)
    license = LicenseSerializer(required=False, read_only=True)
    file = FileSerializer(required=False, read_only=True)
    photographer = PhotographerSerializer(required=False, read_only=True)

    class Meta:
        model = Medium
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["file"] = MediumForView.large_resolution_url(instance)

        return representation
