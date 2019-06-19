from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView
from main.models import Photo, PhotoResized, Tag
from django.db.models import Q


from main.spi_s3_utils import SpiS3Utils
import main.utils as utils


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        total_photos = Photo.objects.count()
        total_thumbnails = PhotoResized.objects.filter(size_label="T").count()
        tags = Tag.objects.order_by("tag")

        context['total_number_photos'] = total_photos
        context['total_number_thumbnails'] = total_thumbnails
        context['list_of_tags'] = tags

        return context


class Search(TemplateView):
    template_name = "search.tmpl"

    def get_context_data(self, **kwargs):
        spi_s3_utils = SpiS3Utils("thumbnails")

        context = super(Search, self).get_context_data(**kwargs)

        query_photos_for_tag = Photo.objects.filter(tags__id=kwargs["tag_id"])

        context["tag_name"] = Tag.objects.get(id=kwargs["tag_id"])
        context["total_number_photos_tag"] = len(query_photos_for_tag)

        photo_result_list = []
        for photo in query_photos_for_tag:
            thumbnail = PhotoResized.objects.filter(photo=photo).filter(size_label="T")

            if len(thumbnail) == 1:
                thumbnail_key = thumbnail[0].object_storage_key
                thumbnail_img = spi_s3_utils.get_presigned_jpeg_link(thumbnail_key)

            else:
                # Images should have a thumbnail
                # TODO: have a placeholder
                thumbnail_img = None

            photo_result = {}

            photo_result['thumbnail'] = thumbnail_img
            photo_result['url'] = photo.object_storage_key
            photo_result['id'] = photo.id

            photo_result_list.append(photo_result)

        context["photos"] = photo_result_list

        return context


def information_for_tag_ids(tag_ids):
    spi_s3_utils = SpiS3Utils("thumbnails")

    information = {}

    query_photos_for_tags = Photo.objects

    for tag_id in tag_ids:
        query_photos_for_tags = query_photos_for_tags.filter(tags__id=int(tag_id))

    information["tag_names"] = "TODO" # Tag.objects.get(id=kwargs["tag_id"])
    information["total_number_photos_tag"] = len(query_photos_for_tags)

    photo_result_list = []
    for photo in query_photos_for_tags:
        thumbnail = PhotoResized.objects.filter(photo=photo).filter(size_label="T")

        if len(thumbnail) == 1:
            thumbnail_key = thumbnail[0].object_storage_key
            thumbnail_img = spi_s3_utils.get_presigned_jpeg_link(thumbnail_key)

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
    def post(self, request, *args, **kwargs):

        list_of_tag_ids = request.POST.getlist('tags')

        information = information_for_tag_ids(list_of_tag_ids)

        return render(request, "search.tmpl", information)


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        spi_s3_thumbnails = SpiS3Utils("thumbnails")
        spi_s3_photos = SpiS3Utils("photos")

        photo_resized_all = PhotoResized.objects.filter(photo__id=kwargs['photo_id'])

        sizes_presentation = []

        for photo_resized in photo_resized_all:
            if photo_resized.size_label == "T":
                continue

            size_information = {}

            size_information['label'] = utils.image_size_label_abbreviation_to_presentation(photo_resized.size_label)
            size_information['size'] = int(photo_resized.file_size / 1024)
            size_information['width'] = photo_resized.width
            size_information['resolution'] = "{}x{}".format(photo_resized.width, photo_resized.height)
            size_information['image_link'] = spi_s3_thumbnails.get_presigned_jpeg_link(photo_resized.object_storage_key)

            sizes_presentation.append(size_information)

        sizes_presentation = sorted(sizes_presentation, key=lambda k: k['width'])

        photo_resized_small = PhotoResized.objects.filter(photo__id=kwargs['photo_id']).filter(size_label="S")[0]

        photo = Photo.objects.get(id=kwargs['photo_id'])

        context['photo_small_url'] = spi_s3_thumbnails.get_presigned_jpeg_link(photo_resized_small.object_storage_key)
        context['media_file'] = photo.object_storage_key
        context['original_file'] = spi_s3_photos.get_presigned_jpeg_link(photo.object_storage_key)

        context['sizes_list'] = sizes_presentation

        context['list_of_tags'] = photo.tags.all()

        return context
