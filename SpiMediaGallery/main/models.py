from django.db import models


class Tag(models.Model):
    tag = models.CharField(max_length=256)

    def __str__(self):
        return "{}".format(self.tag)


class Photo(models.Model):
    path = models.CharField(max_length=1024)
    tags = models.ManyToManyField(Tag, blank=True)
    md5 = models.CharField(max_length=32)

    def __str__(self):
        return "{}".format(self.path)