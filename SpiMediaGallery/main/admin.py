from django.contrib import admin
from main.forms import LocationEntryCoordinates
from django.contrib.gis.admin.options import OSMGeoAdmin

import main.models
import main.utils


class MediaAdmin(OSMGeoAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'height', 'width', 'datetime_taken', 'location',
                    'public', 'photographer', 'license', 'media_type', 'duration_mmss', 'tags_list', )
    ordering = ('object_storage_key', 'datetime_taken', 'photographer', 'license', 'media_type', 'duration', 'public', )
    search_fields = ('object_storage_key', 'md5', )

    form = LocationEntryCoordinates

    def tags_list(self, obj):
        return ",".join([t.tag for t in obj.tags.all()])

    def duration_mmss(self, obj):
        return main.utils.seconds_to_minutes_seconds(obj.duration)


class PhotographerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', )
    ordering = ('first_name', 'last_name', )
    search_fields = ('first_name', 'last_name', )


class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', )
    ordering = ('name', )
    search_fields = ('name', )


class CopyrightAdmin(admin.ModelAdmin):
    list_display = ('holder', 'public_text', )
    ordering = ('holder', )
    search_fields = ('holder', 'public_text', )


class TagAdmin(admin.ModelAdmin):
    list_display = ('tag', )
    ordering = ('tag', )
    search_fields = ('tag', )


class MediaResizedAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'size_label', 'height', 'width', 'media', )
    ordering = ('object_storage_key', )
    search_fields = ('object_storage_key', 'md5', )


admin.site.register(main.models.Media, MediaAdmin)
admin.site.register(main.models.Tag, TagAdmin)
admin.site.register(main.models.MediaResized, MediaResizedAdmin)
admin.site.register(main.models.Photographer, PhotographerAdmin)
admin.site.register(main.models.License, LicenseAdmin)
admin.site.register(main.models.Copyright, CopyrightAdmin)