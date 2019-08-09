# from django.db import models
from django.contrib.gis.db import models
from django.urls import reverse
from django.dispatch import receiver

from main.spi_s3_utils import SpiS3Utils

import os


class Photographer(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)


class License(models.Model):
    name = models.CharField(max_length=255)
    public_text = models.TextField()

    def __str__(self):
        return self.name


class Copyright(models.Model):
    holder = models.CharField(max_length=255)
    public_text = models.TextField(help_text="Text displayed to the user for the copyright holder")

    def __str__(self):
        return self.holder


class Tag(models.Model):
    tag = models.CharField(max_length=255)

    def __str__(self):
        return self.tag


class File(models.Model):
    ORIGINAL = "O"
    PROCESSED = "P"

    BUCKET_NAMES = (
        (ORIGINAL, 'Original'),
        (PROCESSED, 'Processed'),
    )

    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(null=True, blank=True, max_length=32)
    size = models.BigIntegerField()
    bucket = models.CharField(max_length=1, choices=BUCKET_NAMES, null=False, blank=True, default=None)

    def __str__(self):
        return self.object_storage_key

    def bucket_name(self):
        if self.bucket == File.ORIGINAL:
            return "original"
        elif self.bucket == File.PROCESSED:
            return "processed"
        else:
            assert False


@receiver(models.signals.post_delete, sender=File)
def delete_file(sender, instance, *args, **kwargs):
    spi_s3_utils = SpiS3Utils(instance.bucket_name())
    spi_s3_utils.delete(instance.object_storage_key)


class Medium(models.Model):
    PHOTO = 'P'
    VIDEO = 'V'

    MEDIUM_TYPES = (
        (PHOTO, "Photo"),
        (VIDEO, "Video")
    )

    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.PROTECT)

    location = models.PointField(null=True, blank=True)

    height = models.IntegerField(null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    datetime_taken = models.DateTimeField(null=True, blank=True)
    datetime_imported = models.DateTimeField()

    public = models.BooleanField(default=False)
    photographer = models.ForeignKey(Photographer, null=True, on_delete=models.PROTECT)
    license = models.ForeignKey(License, null=True, blank=True, on_delete=models.PROTECT)
    copyright = models.ForeignKey(Copyright, null=True, blank=True, on_delete=models.PROTECT)

    tags = models.ManyToManyField(Tag, blank=True)

    medium_type = models.CharField(max_length=1, choices=MEDIUM_TYPES)

    duration = models.IntegerField(null=True, blank=True)

    def latitude(self):
        if self.location is None:
            return None

        return self.location.y

    def longitude(self):
        if self.location is None:
            return None

        return self.location.x

    class Meta:
        verbose_name_plural = "Media"

    def get_absolute_url(self):
        return reverse('medium', args=[str(self.pk)])

    def __str__(self):
        return "{}".format(self.pk)


class MediumResized(models.Model):
    THUMBNAIL = "T"
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"
    ORIGINAL = "O"

    SIZES_OF_MEDIA = (
        (THUMBNAIL, 'Thumbnail'),
        (SMALL, 'Small'),
        (MEDIUM, 'Medium'),
        (LARGE, 'Large'),
        (ORIGINAL, 'Original')
    )

    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.PROTECT)

    # object_storage_key = models.CharField(max_length=1024)
    # md5 = models.CharField(max_length=32)
    # file_size = models.BigIntegerField()

    datetime_resized = models.DateTimeField()

    size_label = models.CharField(max_length=1, choices=SIZES_OF_MEDIA)

    height = models.IntegerField()
    width = models.IntegerField()
    medium = models.ForeignKey(Medium, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "MediaResized"