# from django.db import models
from django.contrib.gis.db import models
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .spi_s3_utils import SpiS3Utils


class Photographer(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name()

    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    class Meta:
        unique_together = (('first_name', 'last_name'))


class License(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    name = models.CharField(max_length=255, unique=True)
    spdx_identifier = models.CharField(max_length=100,
                                       help_text='Identifier as per https://spdx.org/licenses/ CC-BY-NC-SA-4.0',
                                       unique=True, null=True, blank=True)
    public_text = models.TextField()

    def __str__(self):
        return self.name


class Copyright(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    holder = models.CharField(max_length=255, unique=True)
    public_text = models.TextField(help_text='Text displayed to the user for the copyright holder')

    def __str__(self):
        return self.holder


class TagName(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    XMP = 'X'
    GENERATED = 'G'
    MANUAL = 'M'
    RENAMED = 'R'

    IMPORTER = (
        (XMP, 'XMP'),
        (GENERATED, 'Generated'),
        (MANUAL, 'Manual'),
        (RENAMED, 'Renamed')
    )

    name = models.ForeignKey(TagName, on_delete=models.PROTECT)
    importer = models.CharField(max_length=1, choices=IMPORTER, null=False, blank=False)

    def __str__(self):
        return '{} -{}'.format(self.name, self.importer_name())

    def importer_name(self):
        for importer in self.IMPORTER:
            if importer[0] == self.importer:
                return importer[1]

    class Meta:
        unique_together = (('name', 'importer'),)


class File(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    ORIGINAL = 'O'
    PROCESSED = 'P'
    IMPORTED = 'I'

    BUCKET_NAMES = (
        (ORIGINAL, 'Original'),
        (PROCESSED, 'Processed'),
        (IMPORTED, 'Imported'),
    )

    object_storage_key = models.CharField(max_length=1024)
    md5 = models.CharField(null=True, blank=True, db_index=True, max_length=32)
    size = models.BigIntegerField()
    bucket = models.CharField(max_length=1, choices=BUCKET_NAMES, null=False, blank=False)

    def __str__(self):
        return self.object_storage_key

    def bucket_name(self):
        if self.bucket == File.ORIGINAL:
            return 'original'
        elif self.bucket == File.PROCESSED:
            return 'processed'
        elif self.bucket == File.IMPORTED:
            return 'imported'
        else:
            assert False

    def download_file(self):
        spi_s3_utils = SpiS3Utils(self.bucket_name())

        # TODO: if not having the replace the filename in the S3 response is
        # the filename until the first space.
        # Even though using curl this can be seen:
        # Content-Disposition: attachment; filename=carles test.jpg
        filename = self.object_storage_key.replace(' ', '_')
        url = spi_s3_utils.get_presigned_download_link(self.object_storage_key, filename=filename)

        return mark_safe('<a href="{}">Download</a>'.format(escape(url)))


# @receiver(models.signals.post_delete, sender=File)
# def delete_file(sender, instance, *args, **kwargs):
#    spi_s3_utils = SpiS3Utils(instance.bucket_name())
#    try:
#        spi_s3_utils.delete(instance.object_storage_key)
#    except ClientError:
#        # Boto3 raises ClientError(AccessDenied) if the file is not there
#        pass


class Medium(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    PHOTO = 'P'
    VIDEO = 'V'

    MEDIUM_TYPES = (
        (PHOTO, 'Photo'),
        (VIDEO, 'Video')
    )

    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.PROTECT)

    location = models.PointField(null=True, blank=True, help_text='Location where the photo/video was taken')

    height = models.IntegerField(null=True, blank=True, help_text='Height of the image/video')
    width = models.IntegerField(null=True, blank=True, help_text='Width of the image/video')
    datetime_taken = models.DateTimeField(null=True, blank=True)
    datetime_imported = models.DateTimeField()

    public = models.BooleanField(default=False)
    photographer = models.ForeignKey(Photographer, null=True, on_delete=models.PROTECT)
    license = models.ForeignKey(License, null=True, blank=True, on_delete=models.PROTECT)
    copyright = models.ForeignKey(Copyright, null=True, blank=True, on_delete=models.PROTECT)

    tags = models.ManyToManyField(Tag, blank=True)

    medium_type = models.CharField(max_length=1, choices=MEDIUM_TYPES)

    duration = models.IntegerField(null=True, blank=True, help_text='Duration of the videos, None for photos')

    def latitude(self):
        if self.location is None:
            return None

        return self.location.y

    def longitude(self):
        if self.location is None:
            return None

        return self.location.x

    def preview(self):
        from main.medium_for_view import MediumForView
        medium_for_view: MediumForView = MediumForView.objects.get(id=self.pk)

        if medium_for_view.medium_type == Medium.PHOTO:
            return mark_safe('<img src="{}">'.format(escape(medium_for_view.thumbnail_url())))
        elif medium_for_view.medium_type == Medium.VIDEO:
            return mark_safe('''<video controls>
                <source src='{}'> type="{}"
            </video>
            '''.format(escape(medium_for_view.thumbnail_url()), escape(medium_for_view.thumbnail_content_type())))
        else:
            assert False

    def update_fields(self, fields):
        set_fields(self, fields)

    def get_absolute_url(self):
        return reverse('medium', args=[str(self.pk)])

    def __str__(self):
        return '{}'.format(self.pk)

    class Meta:
        verbose_name_plural = 'Media'


class MediumResized(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    THUMBNAIL = 'T'
    SMALL = 'S'
    MEDIUM = 'M'  # Currently unused
    LARGE = 'L'
    ORIGINAL = 'O'

    SIZES_OF_MEDIA = (
        (THUMBNAIL, 'Thumbnail'),
        (SMALL, 'Small'),
        (MEDIUM, 'Medium'),
        (LARGE, 'Large'),
        (ORIGINAL, 'Original')
    )

    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.PROTECT)

    datetime_resized = models.DateTimeField()

    size_label = models.CharField(max_length=1, choices=SIZES_OF_MEDIA)

    height = models.IntegerField(help_text='Height of this resized medium')
    width = models.IntegerField(help_text='Width of this resized medium')
    medium = models.ForeignKey(Medium, on_delete=models.PROTECT, help_text='Medium that this Resized is from')

    class Meta:
        verbose_name_plural = 'MediaResized'


class TagRenamed(models.Model):
    objects = models.Manager()  # Helps Pycharm CE auto-completion

    old_name = models.CharField(max_length=255, null=True, blank=True)
    new_name = models.CharField(max_length=255, null=True, blank=True)
    datetime_renamed = models.DateTimeField()

    def __str__(self):
        return 'O: {} - N: {}'.format(self.old_name, self.new_name)


class RemoteMedium(models.Model):
    class ApiSource(models.TextChoices):
        PROJECT_APPLICATION_API = 'PROJECT_APPLICATION', 'Project Application'

    medium = models.ForeignKey(Medium, on_delete=models.PROTECT)
    remote_modified_on = models.DateTimeField(help_text='Remote modified_on')
    remote_id = models.IntegerField(help_text='ID of this Medium on the remote side')

    api_source = models.CharField(choices=ApiSource.choices,
                                  default=ApiSource.PROJECT_APPLICATION_API,
                                  help_text='Which API this photos was fetched from',
                                  max_length=20)
    remote_blob = models.TextField(help_text='Remote information for this Medium. The format depends on the '
                                             'api_source. Kept in case that we need to re-process photos')

    def update_fields(self, fields):
        set_fields(self, fields)

    class Meta:
        verbose_name_plural = 'RemoteMedia'


class SyncToken(models.Model):
    class TokenNames(models.TextChoices):
        DELETED_MEDIA_LAST_SYNC = 'DELETED_MEDIA_LAST_SYNC', 'Deleted Media Last Sync'

    token_name = models.CharField(max_length=32, choices=TokenNames.choices)
    token_value = models.CharField(max_length=128, null=True, blank=True)


def set_fields(obj, fields):
    for field_name, value in fields.items():
        setattr(obj, field_name, value)
