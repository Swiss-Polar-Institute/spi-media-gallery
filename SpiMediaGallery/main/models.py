from django.db import models


class Tag(models.Model):
    tag = models.CharField(max_length=256)

    def __str__(self):
        return "{}".format(self.tag)


# class Thumbnail(models.Model):
#     height = models.IntegerField()
#     width = models.IntegerField()
#     object_storage_key = models.CharField(max_length=1024)
#     md5 = models.CharField(max_length=32)
#
#     def __str__(self):
#         return "{}".format(self.object_storage_key)


class Photo(models.Model):
    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(null=True, max_length=32)
    file_size = models.IntegerField()

    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)

    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return "{}".format(self.object_storage_key)


SIZES_OF_PHOTOS = (
    ('T', 'Thumbnail'),
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large')
)

class PhotoResized(models.Model):
    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(max_length=32)
    file_size = models.IntegerField()

    size_label = models.CharField(max_length=1, choices=SIZES_OF_PHOTOS)

    height = models.IntegerField()
    width = models.IntegerField()
    photo = models.OneToOneField(Photo, on_delete=models.PROTECT)