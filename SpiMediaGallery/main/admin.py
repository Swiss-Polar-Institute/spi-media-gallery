from django.contrib import admin
from main.forms import LocationEntryCoordinates
from django.contrib.gis.admin.options import OSMGeoAdmin

import main.models
import main.utils


class MediumAdmin(OSMGeoAdmin):
    list_display = ('file_object_storage_key', 'file_md5', 'file_size', 'height', 'width', 'datetime_taken', 'location',
                    'public', 'photographer', 'license', 'medium_type', 'duration_mmss', 'tags_list',
                    'datetime_imported', )
    ordering = ('file__object_storage_key', 'file__size', 'datetime_taken', 'photographer', 'license', 'medium_type',
                'duration', 'public', 'datetime_imported', )
    search_fields = ('file__object_storage_key', 'file__md5', )
    raw_id_fields = ('file', )
    list_select_related = ('file',)

    form = LocationEntryCoordinates

    def tags_list(self, obj):
        return ",".join([t.tag for t in obj.tags.all()])

    def duration_mmss(self, obj):
        return main.utils.seconds_to_minutes_seconds(obj.duration)

    def file_object_storage_key(self, obj):
        return obj.file.object_storage_key

    def file_md5(self, obj):
        return obj.file.md5

    def file_size(self, obj):
        return main.utils.bytes_to_human_readable(obj.file.size)

    file_size.admin_order_field = 'file__size'
    duration_mmss.admin_order_field = 'duration'


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


class MediumResizedAdmin(admin.ModelAdmin):
    list_display = ('file_object_storage_key', 'file_md5', 'file_size', 'size_label', 'height', 'width', 'medium',
                    'datetime_resized', )
    ordering = ('file__object_storage_key', 'file__size', 'size_label', 'height', 'width', 'medium',
                'datetime_resized', )
    search_fields = ('file__object_storage_key', 'file__md5', )
    raw_id_fields = ('file',)
    list_select_related = ('file', )

    def file_object_storage_key(self, obj):
        if obj.file is None:
            return None
        else:
            return obj.file.object_storage_key

    def file_md5(self, obj):
        if obj.file is None:
            return None
        else:
            return obj.file.md5

    def file_size(self, obj):
        if obj.file is None:
            return None
        else:
            return obj.file.size


class FileAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'md5', 'size', )
    ordering = ('object_storage_key', 'size', )
    search_fields = ('object_storage_key', 'md5', 'size', 'bucket', )


admin.site.register(main.models.Medium, MediumAdmin)
admin.site.register(main.models.Tag, TagAdmin)
admin.site.register(main.models.MediumResized, MediumResizedAdmin)
admin.site.register(main.models.Photographer, PhotographerAdmin)
admin.site.register(main.models.License, LicenseAdmin)
admin.site.register(main.models.Copyright, CopyrightAdmin)
admin.site.register(main.models.File, FileAdmin)