from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from main.models import Media, MediaResized, Tag
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

        total_photos = Media.objects.count()
        total_thumbnails = MediaResized.objects.filter(size_label="T").count()
        size_of_photos = utils.bytes_to_human_readable(Media.objects.aggregate(Sum('file_size'))['file_size__sum'])

        tags = []
        for tag in Tag.objects.order_by("tag"):
            t = {}
            t['id'] = tag.id
            t['tag'] = tag.tag
            t['count'] = Media.objects.filter(tags__id=tag.id).count()

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
        photo = Media.objects.order_by('?')[0]

        return redirect("/display/{}".format(photo.id))


def information_for_photo_queryset(photo_queryset):
    media_result_list = []
    for photo in photo_queryset[:200]:
        thumbnail = MediaResized.objects.filter(media=photo).filter(size_label="T")

        filename = "SPI-{}.jpg".format(photo.id)

        if len(thumbnail) == 1:
            thumbnail_img = link_for_media(thumbnail[0], "inline", filename)

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

    query_photos_for_tags = Media.objects
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
            photo = Media.objects.get(id=photo_id)
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

        query_photos_in_geom = Media.objects.filter(location__contained=geom)

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

        query_photos_nearby = Media.objects.filter(location__within=buffered)

        if len(query_photos_nearby) != 1:
            photos_string = "photos"
        else:
            photos_string = "photo"

        information = {}
        information["search_explanation"] = "{} {} in a radius of {} Km from latitude: {:.2f} longitude: {:.2f}".format(len(query_photos_nearby),
                                                                                                                        photos_string, km, latitude, longitude)

        information["photos"] = information_for_photo_queryset(query_photos_nearby)

        return render(request, "search.tmpl", information)



class SearchVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information["search_explanation"] = "Videos"

        media = []

        for video in Media.objects.filter(media_type=Media.VIDEO):
            low_resolution_qs = MediaResized.objects.filter(size_label=MediaResized.SMALL).filter(media=video)

            if len(low_resolution_qs) != 1:
                continue

            low_resolution = low_resolution_qs[0]

            media.append({'id': video.pk,
                          'key': video.object_storage_key,
                          'duration': utils.seconds_to_minutes_seconds(video.duration),
                          'low_resolution': link_for_media(low_resolution, "inline", filename_for_resized_media(video.pk, "S", "webm")),
                          'low_resolution_file_size': utils.bytes_to_human_readable(low_resolution.file_size),
                          'original': link_for_media(video, "attachment", filename_for_original_media(video)),
                          'original_file_size': utils.bytes_to_human_readable(video.file_size)})

        information['media'] = media
        return render(request, "search_text.tmpl", information)


def link_for_media(medium, content_disposition, filename):
    if type(medium) == MediaResized:
        medium_for_content_type = medium.media
    else:
        medium_for_content_type = medium

    if medium_for_content_type.media_type == Media.PHOTO:
        content_type = "image/jpeg"
    elif medium_for_content_type.media_type == Media.VIDEO:
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


def filename_for_resized_media(media_id, photo_resize_label, extension):
    return "SPI-{}-{}.{}".format(media_id, photo_resize_label, extension)


def filename_for_original_media(media):
    _, extension = os.path.splitext(media.object_storage_key)

    extension = extension[1:]

    return "SPI-{}.{}".format(media.pk, extension)


def information_for_media(media):
    information = {}

    photo_resized_all = MediaResized.objects.filter(media=media)

    sizes_presentation = []

    for photo_resized in photo_resized_all:
        if photo_resized.size_label == "T":
            continue

        size_information = {}

        size_information['label'] = utils.image_size_label_abbreviation_to_presentation(photo_resized.size_label)
        size_information['size'] = utils.bytes_to_human_readable(photo_resized.file_size)
        size_information['width'] = photo_resized.width
        size_information['resolution'] = "{}x{}".format(photo_resized.width, photo_resized.height)

        if media.media_type == Media.PHOTO:
            extension = "jpg"
        elif media.media_type == Media.VIDEO:
            extension = "webm"
        else:
            assert False

        filename = filename_for_resized_media(media.id, photo_resized.size_label, extension)

        size_information['image_link'] = link_for_media(photo_resized, "inline", filename)

        sizes_presentation.append(size_information)

        if photo_resized.size_label == "S":
            if media.media_type == Media.PHOTO:
                information['photo_small_url'] = link_for_media(photo_resized, "inline", filename)
            elif media.media_type == Media.VIDEO:
                information['video_small_url'] = link_for_media(photo_resized, "inline", filename)
            else:
                assert False

    information['sizes_list'] = sorted(sizes_presentation, key=lambda k: k['width'])

    _, file_extension = os.path.splitext(media.object_storage_key)
    file_extension = file_extension.replace(".", "")
    information['file_id'] = "SPI-{}.{}".format(media.id, file_extension)

    information['original_file'] = link_for_media(media, "attachment", "SPI-{}.{}".format(media.id, file_extension))
    information['original_resolution'] = "{}x{}".format(media.width, media.height)
    information['original_file_size'] = utils.bytes_to_human_readable(media.file_size)

    information['date_taken'] = media.datetime_taken

    information['photo_latitude'] = media.latitude()
    information['photo_longitude'] = media.longitude()
    information['media_type'] = media.media_type

    list_of_tags = []

    for tag in media.tags.all():
        t = {'id': tag.id, 'tag': tag.tag}
        list_of_tags.append(t)

    information['list_of_tags'] = sorted(list_of_tags, key=lambda k: k['tag'])

    if media.license is not None:
        information['license'] = media.license.public_text
    else:
        information['license'] = "Unknown"

    if media.copyright is not None:
        information['copyright'] = media.copyright.public_text
    else:
        information['copyright'] = "Unknown"

    if media.photographer is not None:
        information['photographer'] = "{} {}".format(media.photographer.first_name, media.photographer.last_name)
    else:
        information['photographer'] = "Unknown"

    return information


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        context.update(information_for_media(Media.objects.get(id=kwargs['photo_id'])))

        return context


class Map(TemplateView):
    template_name = "map.tmpl"

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        return context


class PhotosGeojson(View):
    def get(self, request):
        serialized = serialize('geojson', Media.objects.all(), geometry_field="location", fields=('pk',))
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
            photo = Media.objects.get(md5=kwargs['md5'])
        elif bucket_name == "thumbnails":
            photo = MediaResized.objects.get(md5=kwargs['md5'])
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
