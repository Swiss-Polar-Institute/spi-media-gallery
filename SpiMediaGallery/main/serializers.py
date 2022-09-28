from django.utils import timezone
from rest_framework import serializers

from .models import Medium, Tag
from .utils import set_tags


class TageSerializer(serializers.ModelSerializer):
    importer = serializers.CharField(default="M")
    name = serializers.CharField(source="name.name")

    class Meta:
        model = Tag
        fields = "__all__"


class MediumSerializer(serializers.ModelSerializer):
    tags = TageSerializer(required=False, many=True)
    datetime_imported = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = Medium
        fields = "__all__"

    def create(self, validated_data):
        medium = Medium.objects.create(**validated_data)
        tags_name = [
            self.initial_data[tag] for tag in self.initial_data if tag.startswith("tag")
        ]
        set_tags(medium, tags_name, "M")
        return medium
