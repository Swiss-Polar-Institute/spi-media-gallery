from django.db import models


class Tag(models.Model):
    tag = models.CharField(max_length=256)

    def __str__(self):
        return "{}".format(self.tag)


class Photo(models.Model):
    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(null=True, max_length=32)
    file_size = models.IntegerField()

    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)
    datetime_taken = models.DateTimeField(null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return "{}".format(self.object_storage_key)


class PhotoResized(models.Model):
    THUMBNAIL = "T"
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"
    ORIGINAL = "O"

    SIZES_OF_PHOTOS = (
        (THUMBNAIL, 'Thumbnail'),
        (SMALL, 'Small'),
        (MEDIUM, 'Medium'),
        (LARGE, 'Large'),
        (ORIGINAL, 'Original')
    )

    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(max_length=32)
    file_size = models.IntegerField()

    size_label = models.CharField(max_length=1, choices=SIZES_OF_PHOTOS)

    height = models.IntegerField()
    width = models.IntegerField()
    photo = models.ForeignKey(Photo, on_delete=models.PROTECT)