from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from main.models import Photo, PhotoResized, Tag
from django.db.models import Sum
from main.forms import PhotoIdForm
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

from django.contrib.gis.geos import Point
from django.contrib.gis.geos import Polygon

from django.core.serializers import serialize

# from djeo
# from djgeojson.views import GeoJSONLayerView

import json

import os
import re

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
        context['form_search_photo_id'] = PhotoIdForm

        return context


class Random(TemplateView):
    template_name = "display.tmpl"

    def get(self, request, *args, **kwargs):
        photo = Photo.objects.order_by('?')[0]

        return redirect("/display/{}".format(photo.id))


def information_for_photo_queryset(photo_queryset):
    spi_s3_utils = SpiS3Utils("thumbnails")

    photo_result_list = []
    for photo in photo_queryset[:200]:
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

    return photo_result_list


def information_for_tag_ids(tag_ids):
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

    information["photos"] = information_for_photo_queryset(query_photos_for_tags)

    return information


class SearchMultipleTags(TemplateView):
    def get(self, request, *args, **kwargs):
        list_of_tag_ids = request.GET.getlist('tags')

        information = information_for_tag_ids(list_of_tag_ids)

        return render(request, "search.tmpl", information)


class SearchPhotoId(TemplateView):
    def post(self, request, *args, **kwargs):
        photo_id = request.POST["photo_id"]

        photo_id = photo_id.split(".")[0]

        photo_id = int(re.findall("\d+", photo_id)[0])

        try:
            photo = Photo.objects.get(id=photo_id)
        except ObjectDoesNotExist:
            template_information = {}
            template_information['photo_id_not_found'] = photo_id
            template_information['form_search_photo_id'] = PhotoIdForm

            return render(request, "error_photo_id_not_found.tmpl", template_information)

        return redirect("/display/{}".format(photo.id))

class SearchBox(TemplateView):
    def get(self, request, *args, **kwargs):
        north = float(request.GET["north"])
        south = float(request.GET["south"])
        east = float(request.GET["east"])
        west = float(request.GET["west"])

        information = {}

        # ne_point = Point(east, north, srid=4326)
        # sw_point = Point(west, south, srid=4326)

        geom = Polygon.from_bbox((east, south, west, north))

        query_photos_for_tags = Photo.objects.filter(location__contained=geom)

        information["total_number_photos_tag"] = len(query_photos_for_tags)

        information["photos"] = information_for_photo_queryset(query_photos_for_tags)

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
    file_extension = file_extension.replace(".", "")
    information['file_id'] = "SPI-{}.{}".format(photo.id, file_extension)

    information['original_file'] = spi_s3_photos.get_presigned_download_link(photo.object_storage_key, "SPI-{}.{}".format(photo.id, file_extension))
    information['original_resolution'] = "{}x{}".format(photo.width, photo.height)
    information['original_file_size'] = utils.bytes_to_human_readable(photo.file_size)

    information['date_taken'] = photo.datetime_taken

    list_of_tags = []

    for tag in photo.tags.all():
        t = {'id': tag.id, 'tag': tag.tag}
        list_of_tags.append(t)

    information['list_of_tags'] = sorted(list_of_tags, key=lambda k: k['tag'])

    information['license'] = photo.license.public_text

    if photo.copyright is not None:
        information['copyright'] = photo.copyright.public_text
    else:
        information['copyright'] = "Unknown"

    information['photographer'] = "{} {}".format(photo.photographer.first_name, photo.photographer.last_name)

    return information


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        context.update(information_for_photo(Photo.objects.get(id=kwargs['photo_id'])))

        return context


class Map(TemplateView):
    template_name = "map.tmpl"

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        return context


class PhotosGeojson(View):
    def get(self, request):
        serialized = serialize('geojson', Photo.objects.all(), geometry_field="location", fields=('pk', ))
        return JsonResponse(json.loads(serialized))

class TrackGeojson(View):
    def get(self, request_):
        track = open(settings.TRACK_MAP_FILEPATH, "r")
        return JsonResponse(json.load(track))
