from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView
from main.models import Photo, PhotoResized, Tag
from django.db.models import Sum

import os

from main.spi_s3_utils import SpiS3Utils
import main.utils as utils


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        total_photos = Photo.objects.count()
        total_thumbnails = PhotoResized.objects.filter(size_label="T").count()
        size_of_photos = utils.bytes_to_human_readable(Photo.objects.aggregate(Sum('file_size'))['file_size__sum'])

        tags = []
        for tag in Tag.objects.order_by("tag"):
            t = {}
            t['id'] = tag.id
            t['tag'] = tag.tag
            t['count'] = Photo.objects.filter(tags__id=tag.id).count()

            tags.append(t)

        # tags = Tag.objects.order_by("tag")

        context['total_number_photos'] = total_photos
        context['total_number_thumbnails'] = total_thumbnails
        context['size_of_photos'] = size_of_photos
        context['list_of_tags'] = tags
        context['list_of_tags_first_half'] = tags[:int(1+len(tags)/2)]
        context['list_of_tags_second_half'] = tags[int(1+len(tags)/2):]

        return context


class Random(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Random, self).get_context_data(**kwargs)

        photo = Photo.objects.order_by('?')[0]

        context.update(information_for_photo(photo))

        return context


def information_for_tag_ids(tag_ids):
    spi_s3_utils = SpiS3Utils("thumbnails")

    information = {}

    query_photos_for_tags = Photo.objects
    tags_list = []

    for tag_id in tag_ids:
        query_photos_for_tags = query_photos_for_tags.filter(tags__id=int(tag_id))
        tags_list.append(Tag.objects.get(id=tag_id).tag)

    information["tags_list"] = ", ".join(tags_list) # Tag.objects.get(id=kwargs["tag_id"])
    information["total_number_photos_tag"] = len(query_photos_for_tags)

    if len(tag_ids) != 1:
        information["this_tag"] = "these tags"
    else:
        information["this_tag"] = "this tag"

    photo_result_list = []
    for photo in query_photos_for_tags[:200]:
        thumbnail = PhotoResized.objects.filter(photo=photo).filter(size_label="T")

        if len(thumbnail) == 1:
            thumbnail_key = thumbnail[0].object_storage_key
            filename = "SPI-{}.jpg".format(photo.id)
            thumbnail_img = spi_s3_utils.get_presigned_jpeg_link(thumbnail_key, filename)

        else:
            # Images should have a thumbnail
            # TODO: have a placeholder
            thumbnail_img = None

        photo_result = {}

        photo_result['thumbnail'] = thumbnail_img
        photo_result['url'] = photo.object_storage_key
        photo_result['id'] = photo.id

        photo_result_list.append(photo_result)

    information["photos"] = photo_result_list

    return information


class SearchMultipleTags(TemplateView):
    def get(self, request, *args, **kwargs):
        list_of_tag_ids = request.GET.getlist('tags')

        information = information_for_tag_ids(list_of_tag_ids)

        return render(request, "search.tmpl", information)


def information_for_photo(photo):
    information = {}

    spi_s3_thumbnails = SpiS3Utils("thumbnails")
    spi_s3_photos = SpiS3Utils("photos")

    photo_resized_all = PhotoResized.objects.filter(photo=photo)

    sizes_presentation = []

    for photo_resized in photo_resized_all:
        if photo_resized.size_label == "T":
            continue

        size_information = {}

        size_information['label'] = utils.image_size_label_abbreviation_to_presentation(photo_resized.size_label)
        size_information['size'] = utils.bytes_to_human_readable(photo_resized.file_size)
        size_information['width'] = photo_resized.width
        size_information['resolution'] = "{}x{}".format(photo_resized.width, photo_resized.height)
        filename = "SPI-{}-{}.jpg".format(photo.id, photo_resized.size_label)
        size_information['image_link'] = spi_s3_thumbnails.get_presigned_jpeg_link(photo_resized.object_storage_key, filename)

        sizes_presentation.append(size_information)

        if photo_resized.size_label == "S":
            information['photo_small_url'] = spi_s3_thumbnails.get_presigned_jpeg_link(photo_resized.object_storage_key)

    information['sizes_list'] = sorted(sizes_presentation, key=lambda k: k['width'])

    _, file_extension = os.path.splitext(photo.object_storage_key)
    information['file_id'] = "SPI-{}.{}".format(photo.id, file_extension.replace(".", ""))

    information['original_file'] = spi_s3_photos.get_presigned_download_link(photo.object_storage_key, "SPI-{}.jpg".format(photo.id))
    information['original_resolution'] = "{}x{}".format(photo.width, photo.height)
    information['original_file_size'] = utils.bytes_to_human_readable(photo.file_size)

    information['date_taken'] = photo.datetime_taken

    list_of_tags = []

    for tag in photo.tags.all():
        t = {'id': tag.id, 'tag': tag.tag}
        list_of_tags.append(t)

    information['list_of_tags'] = sorted(list_of_tags, key=lambda k: k['tag'])

    return information


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        context.update(information_for_photo(Photo.objects.get(id=kwargs['photo_id'])))

        return context
