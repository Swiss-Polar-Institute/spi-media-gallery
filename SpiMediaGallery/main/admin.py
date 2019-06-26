from django.contrib import admin
from main.forms import LocationEntryCoordinates
from django.contrib.gis.admin.options import OSMGeoAdmin

import main.models


class PhotoAdmin(OSMGeoAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'height', 'width', 'datetime_taken', 'location', 'tags_list')
    ordering = ['object_storage_key']
    search_fields = ('object_storage_key', 'md5')

    form = LocationEntryCoordinates

    def tags_list(self, obj):
        return ",".join([t.tag for t in obj.tags.all()])


class TagAdmin(admin.ModelAdmin):
    list_display = ('tag', )
    ordering = ['tag']
    search_fields = ('tag', )


class PhotoResizedAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'size_label', 'height', 'width', 'photo')
    ordering = ['object_storage_key']
    search_fields = ('object_storage_key', 'md5', 'photo')


admin.site.register(main.models.Photo, PhotoAdmin)
admin.site.register(main.models.Tag, TagAdmin)
admin.site.register(main.models.PhotoResized, PhotoResizedAdmin)
