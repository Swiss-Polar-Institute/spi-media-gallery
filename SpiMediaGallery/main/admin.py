from django.forms import ModelForm
from django.contrib import admin

import main.models


class PhotoAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'height', 'width', 'datetime_taken', 'tags_list')
    ordering = ['object_storage_key']
    search_fields = ('object_storage_key', 'md5')

    def tags_list(self, obj):
        return ",".join([t.tag for t in obj.tags.all()])


class TagAdmin(admin.ModelAdmin):
    list_display = ('tag', )
    ordering = ['tag']


class PhotoResizedAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'md5', 'file_size', 'size_label', 'height', 'width', 'photo')
    ordering = ['object_storage_key']


admin.site.register(main.models.Photo, PhotoAdmin)
admin.site.register(main.models.Tag, TagAdmin)
admin.site.register(main.models.PhotoResized, PhotoResizedAdmin)
