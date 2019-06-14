from django.db import models


class Tag(models.Model):
    tag = models.CharField(max_length=256)

    def __str__(self):
        return "{}".format(self.tag)


class Thumbnail(models.Model):
    height = models.IntegerField()
    width = models.IntegerField()
    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(max_length=32)

    def __str__(self):
        return "{}".format(self.object_storage_key)


class Photo(models.Model):
    object_storage_key = models.CharField(max_length=1024)
    tags = models.ManyToManyField(Tag, blank=True)
    md5 = models.CharField(max_length=32)
    thumbnail = models.ForeignKey(Thumbnail, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return "{}".format(self.object_storage_key)

