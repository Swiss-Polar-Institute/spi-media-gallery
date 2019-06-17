from django.forms import ModelForm
from django.contrib import admin

import main.models


class PhotoAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'tags_list', 'thumbnail', 'size', 'md5')
    ordering = ['object_storage_key']
    search_fields = ('path', 'tags')

    def tags_list(self, obj):
        return ",".join([t.tag for t in obj.tags.all()])


class TagAdmin(admin.ModelAdmin):
    list_display = ('tag', )
    ordering = ['tag']


class ThumbnailAdmin(admin.ModelAdmin):
    list_display = ('object_storage_key', 'height', 'width', 'md5', )
    ordering = ['object_storage_key']


admin.site.register(main.models.Photo, PhotoAdmin)
admin.site.register(main.models.Tag, TagAdmin)
admin.site.register(main.models.Thumbnail, ThumbnailAdmin)
