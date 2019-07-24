from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from main.models import Medium, MediumResized, Tag
from django.db.models import Sum
from main.forms import PhotoIdForm
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance

from django.core.serializers import serialize

# from djeo
# from djgeojson.views import GeoJSONLayerView

from django.core.paginator import Paginator

import json

import os
import re
import requests
import urllib

from main.spi_s3_utils import SpiS3Utils
import main.utils as utils


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        total_photos = Medium.objects.filter(medium_type=Medium.PHOTO).count()
        total_videos = Medium.objects.filter(medium_type=Medium.VIDEO).count()

        total_photo_thumbnails = MediumResized.objects.filter(size_label="T").filter(medium__medium_type=Medium.PHOTO).count()
        total_video_thumbnails = MediumResized.objects.filter(size_label="S").filter(medium__medium_type=Medium.VIDEO).count()

        size_of_photos = utils.bytes_to_human_readable(Medium.objects.filter(medium_type=Medium.PHOTO).aggregate(Sum('file_size'))['file_size__sum'])
        size_of_videos = utils.bytes_to_human_readable(Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('file_size'))['file_size__sum'])

        tags = []
        for tag in Tag.objects.order_by("tag"):
            t = {}
            t['id'] = tag.id
            t['tag'] = tag.tag
            t['count'] = Medium.objects.filter(tags__id=tag.id).count()

            tags.append(t)

        context['total_number_photos'] = total_photos
        context['total_number_videos'] = total_videos

        context['total_number_photo_thumbnails'] = total_photo_thumbnails
        context['total_number_video_thumbnails'] = total_video_thumbnails

        context['size_of_photos'] = size_of_photos
        context['size_of_videos'] = size_of_videos

        context['list_of_tags'] = tags

        context['list_of_tags_first_half'] = tags[:int(1+len(tags)/2)]
        context['list_of_tags_second_half'] = tags[int(1+len(tags)/2):]

        context['form_search_photo_id'] = PhotoIdForm

        return context


class Random(TemplateView):
    template_name = "display.tmpl"

    def get(self, request, *args, **kwargs):
        photo = Medium.objects.order_by('?')[0]

        return redirect("/display/{}".format(photo.id))


def information_for_photo_queryset(photo_queryset):
    media_result_list = []
    for photo in photo_queryset[:200]:
        thumbnail = MediumResized.objects.filter(medium=photo).filter(size_label="T")

        filename = "SPI-{}.jpg".format(photo.id)

        if len(thumbnail) == 1:
            thumbnail_img = link_for_medium(thumbnail[0], "inline", filename)

        else:
            # Images should have a thumbnail
            # TODO: have a placeholder
            thumbnail_img = None

        photo_result = {}

        photo_result['thumbnail'] = thumbnail_img
        photo_result['url'] = photo.object_storage_key
        photo_result['id'] = photo.id

        media_result_list.append(photo_result)

    return media_result_list


def information_for_tag_ids(tag_ids):
    information = {}

    query_photos_for_tags = Medium.objects
    tags_list = []

    for tag_id in tag_ids:
        query_photos_for_tags = query_photos_for_tags.filter(tags__id=int(tag_id))
        tags_list.append(Tag.objects.get(id=tag_id).tag)

    tags_list = ", ".join(tags_list) # Tag.objects.get(id=kwargs["tag_id"])

    if len(query_photos_for_tags) != 1:
        photos_string = "Photos"
    else:
        photos_string = "Photo"

    if len(tag_ids) != 1:
        information["search_explanation"] = "{} {} with these tags: {}".format(len(query_photos_for_tags), photos_string, tags_list)
    else:
        information["search_explanation"] = "{} {} with this tag: {}".format(len(query_photos_for_tags), photos_string, tags_list)

    information["total_number_photos"] = len(query_photos_for_tags)

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
            photo = Medium.objects.get(id=photo_id)
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

        geom = Polygon.from_bbox((east, south, west, north))

        query_photos_in_geom = Medium.objects.filter(location__contained=geom)

        if len(query_photos_in_geom) != 1:
            photos_string = "photos"
        else:
            photos_string = "photo"

        information["search_explanation"] = "{} {} taken in area {:.2f} {:.2f} {:.2f} {:.2f}".format(len(query_photos_in_geom),
                                                                                                    photos_string,
                                                                                                  north, east,
                                                                                                  south, west)

        information["photos"] = information_for_photo_queryset(query_photos_in_geom)

        return render(request, "search.tmpl", information)


def meters_to_degrees(meters):
    return meters / 40000000.0 * 360.0


class SearchNear(TemplateView):
    def get(self, request, *args, **kwargs):
        latitude = float(request.GET["latitude"])
        longitude = float(request.GET["longitude"])
        km = float(request.GET["km"])

        center_point = Point(longitude, latitude, srid=4326)
        buffered = center_point.buffer(meters_to_degrees(km*1000))

        query_photos_nearby = Medium.objects.filter(location__within=buffered)

        if len(query_photos_nearby) != 1:
            photos_string = "photos"
        else:
            photos_string = "photo"

        information = {}
        information["search_explanation"] = "{} {} in a radius of {} Km from latitude: {:.2f} longitude: {:.2f}".format(len(query_photos_nearby),
                                                                                                                        photos_string, km, latitude, longitude)

        information["photos"] = information_for_photo_queryset(query_photos_nearby)

        return render(request, "search.tmpl", information)


class MediumForPagination(Medium):
    def link_for_low_resolution(self):
        return link_for_medium(self._medium_resized("S"), "inline", filename_for_resized_medium(self.pk, "S", "webm"))

    def link_for_original(self):
        return link_for_medium(self, "attachment", filename_for_original_medium(self))

    def file_size_for_original(self):
        return utils.bytes_to_human_readable(self.file_size)

    def _medium_resized(self, label):
        qs = MediumResized.objects.filter(medium=self).filter(size_label=label)
        assert len(qs) < 2

        if len(qs) == 1:
            return qs[0]
        else:
            return None

    def file_size_for_low_resolution(self):
        return utils.bytes_to_human_readable(self._medium_resized("S").file_size)

    def duration_in_minutes_seconds(self):
        return utils.seconds_to_minutes_seconds(self.duration)

    class Meta:
        proxy = True


class SearchVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information["search_explanation"] = "Videos"

        videos_qs = MediumForPagination.objects.filter(medium_type=Medium.VIDEO).order_by("object_storage_key")

        paginator = Paginator(videos_qs, 5)

        page = request.GET.get('page')

        videos = paginator.get_page(page)

        information['media'] = videos

        return render(request, "search_text.tmpl", information)


def link_for_medium(medium, content_disposition, filename):
    if type(medium) == MediumResized:
        medium_for_content_type = medium.medium
    else:
        medium_for_content_type = medium

    if medium_for_content_type.medium_type == Medium.PHOTO:
        content_type = "image/jpeg"
    elif medium_for_content_type.medium_type == Medium.VIDEO:
        content_type = "video/webm"

    if settings.PROXY_TO_OBJECT_STORAGE:
        d = {"content_type": content_type,
             "content_disposition_type": content_disposition,
             "filename": filename,
             "bucket": medium.bucket_name()
        }

        return "/get/photo/{}?{}".format(medium.md5, urllib.parse.urlencode(d))
    else:
        bucket = SpiS3Utils(medium.bucket_name())

        return bucket.get_presigned_link(medium.object_storage_key, content_type, content_disposition, filename)


def filename_for_resized_medium(medium_id, photo_resize_label, extension):
    return "SPI-{}-{}.{}".format(medium_id, photo_resize_label, extension)


def filename_for_original_medium(medium):
    _, extension = os.path.splitext(medium.object_storage_key)

    extension = extension[1:]

    return "SPI-{}.{}".format(medium.pk, extension)


def size_for_medium(medium):
    if medium.width is None or medium.height is None:
        return "Unknown"
    else:
        return "{}x{}".format(medium.width, medium.height)


def information_for_medium(medium):
    information = {}

    medium_resized_all = MediumResized.objects.filter(medium=medium)

    sizes_presentation = []

    for medium_resized in medium_resized_all:
        if medium_resized.size_label == "T":
            continue

        size_information = {}

        size_information['label'] = utils.image_size_label_abbreviation_to_presentation(medium_resized.size_label)
        size_information['size'] = utils.bytes_to_human_readable(medium_resized.file_size)
        size_information['width'] = medium_resized.width

        size_information['resolution'] = size_for_medium(medium_resized)

        if medium.medium_type == Medium.PHOTO:
            extension = "jpg"
        elif medium.medium_type == Medium.VIDEO:
            extension = "webm"
        else:
            assert False

        filename = filename_for_resized_medium(medium.id, medium_resized.size_label, extension)

        size_information['image_link'] = link_for_medium(medium_resized, "inline", filename)

        sizes_presentation.append(size_information)

        if medium_resized.size_label == "S":
            if medium.medium_type == Medium.PHOTO:
                information['photo_small_url'] = link_for_medium(medium_resized, "inline", filename)
            elif medium.medium_type == Medium.VIDEO:
                information['video_small_url'] = link_for_medium(medium_resized, "inline", filename)
            else:
                assert False

    information['sizes_list'] = sorted(sizes_presentation, key=lambda k: k['width'])

    _, file_extension = os.path.splitext(medium.object_storage_key)
    file_extension = file_extension.replace(".", "")
    information['file_id'] = "SPI-{}.{}".format(medium.id, file_extension)

    information['original_file'] = link_for_medium(medium, "attachment", "SPI-{}.{}".format(medium.id, file_extension))
    information['original_resolution'] = size_for_medium(medium)
    information['original_file_size'] = utils.bytes_to_human_readable(medium.file_size)

    information['date_taken'] = medium.datetime_taken

    information['photo_latitude'] = medium.latitude()
    information['photo_longitude'] = medium.longitude()
    information['medium_type'] = medium.medium_type

    list_of_tags = []

    for tag in medium.tags.all():
        t = {'id': tag.id, 'tag': tag.tag}
        list_of_tags.append(t)

    information['list_of_tags'] = sorted(list_of_tags, key=lambda k: k['tag'])

    if medium.license is not None:
        information['license'] = medium.license.public_text
    else:
        information['license'] = "Unknown"

    if medium.copyright is not None:
        information['copyright'] = medium.copyright.public_text
    else:
        information['copyright'] = "Unknown"

    if medium.photographer is not None:
        information['photographer'] = "{} {}".format(medium.photographer.first_name, medium.photographer.last_name)
    else:
        information['photographer'] = "Unknown"

    return information


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        context.update(information_for_medium(Medium.objects.get(id=kwargs['photo_id'])))

        return context


class Map(TemplateView):
    template_name = "map.tmpl"

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        return context


class PhotosGeojson(View):
    def get(self, request):
        serialized = serialize('geojson', Medium.objects.all(), geometry_field="location", fields=('pk',))
        return JsonResponse(json.loads(serialized))


class TrackGeojson(View):
    def get(self, request_):
        track = open(settings.TRACK_MAP_FILEPATH, "r")
        return JsonResponse(json.load(track))


#     path('get/photo_resized/<str:md5>', GetPhoto.as_view())
class GetPhoto(View):
    def get(self, request, *args, **kwargs):
        bucket_name = request.GET['bucket']

        if bucket_name == "photos":
            photo = Medium.objects.get(md5=kwargs['md5'])
        elif bucket_name == "thumbnails":
            photo = MediumResized.objects.get(md5=kwargs['md5'])
        else:
            assert False

        filename = request.GET['filename']
        content_type = request.GET['content_type']
        content_disposition_type = request.GET['content_disposition_type']

        spi_s3 = SpiS3Utils(bucket_name)

        url = spi_s3.get_presigned_link(photo.object_storage_key, content_disposition_type, content_type, filename)

        r = requests.get(url=url, stream=True)
        r.raise_for_status()

        response = HttpResponse(r.raw, content_type=content_type)
        response["Content-Disposition"] = "{}; filename={}".format(content_disposition_type, filename)
        return response


# class GetDownloadFromBucket(View):
#     spi_s3_utils = SpiS3Utils("")
#
#     def get(self, rquest, *args, **kwargs):
#         return None
