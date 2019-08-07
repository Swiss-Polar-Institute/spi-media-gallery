from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from main.models import Medium, MediumResized, Tag
from django.db.models import Sum
from main.forms import MediumIdForm
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
from main.medium_for_view import MediumForView
from django.contrib.gis.geos import Point, Polygon
from django.urls import reverse

from django.core.serializers import serialize

from django.core.paginator import Paginator

import json
import datetime
import os
import re
import requests
import urllib
import csv

from main.spi_s3_utils import SpiS3Utils, link_for_medium
import main.utils as utils


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        tags = []
        for tag in Tag.objects.order_by("tag"):
            t = {}
            t['id'] = tag.id
            t['tag'] = tag.tag
            t['count'] = Medium.objects.filter(tags__id=tag.id).count()

            tags.append(t)

        context['list_of_tags'] = tags

        context['list_of_tags_first_half'] = tags[:int(1+len(tags)/2)]
        context['list_of_tags_second_half'] = tags[int(1+len(tags)/2):]

        context['form_search_medium_id'] = MediumIdForm

        return context


def search_for_nearby(latitude, longitude, km):
    center_point = Point(longitude, latitude, srid=4326)
    buffered = center_point.buffer(meters_to_degrees(km * 1000))

    qs = MediumForView.objects.filter(location__within=buffered)

    if qs.count() != 1:
        photos_string = "media"
    else:
        photos_string = "medium"

    information = {}
    information["search_explanation"] = "{} {} in a radius of {} Km from latitude: {:.2f} longitude: {:.2f}".format(
        qs.count(),
        photos_string, km, latitude, longitude)

    return information, qs


def search_in_box(north, south, east, west):
    geom = Polygon.from_bbox((east, south, west, north))

    qs = MediumForView.objects.filter(location__contained=geom)

    if qs.count() != 1:
        photos_string = "media"
    else:
        photos_string = "medium"

    information = {}

    information["search_explanation"] = "{} {} taken in area {:.2f} {:.2f} {:.2f} {:.2f}".format(
        qs.count(),
        photos_string,
        north, east,
        south, west)

    return information, qs


def search_for_tag_ids(tag_ids):
    information = {}

    query_media_for_tags = MediumForView.objects.order_by("datetime_taken")
    tags_list = []

    for tag_id in tag_ids:
        query_media_for_tags = query_media_for_tags.filter(tags__id=int(tag_id))
        tags_list.append(Tag.objects.get(id=tag_id).tag)

    tags_list = ", ".join(tags_list) # Tag.objects.get(id=kwargs["tag_id"])

    if len(query_media_for_tags) != 1:
        photos_string = "Media"
    else:
        photos_string = "Medium"

    if len(tag_ids) != 1:
        information["search_explanation"] = "{} {} with these tags: {}".format(query_media_for_tags.count(), photos_string, tags_list)
    else:
        information["search_explanation"] = "{} {} with this tag: {}".format(query_media_for_tags.count(), photos_string, tags_list)

    return information, query_media_for_tags


class Search(TemplateView):
    def get(self, request, *args, **kwargs):
        if "tags" in request.GET:
            list_of_tag_ids = request.GET.getlist('tags')
            information, qs = search_for_tag_ids(list_of_tag_ids)

        elif "latitude" in request.GET and "longitude" in request.GET and "km" in request.GET:
            latitude = float(request.GET["latitude"])
            longitude = float(request.GET["longitude"])
            km = float(request.GET["km"])

            information, qs = search_for_nearby(latitude, longitude, km)

        elif "north" in request.GET and "south" in request.GET and "east" in request.GET and "west" in request.GET:
            north = float(request.GET["north"])
            south = float(request.GET["south"])
            east = float(request.GET["east"])
            west = float(request.GET["west"])

            information, qs = search_in_box(north, south, east, west)

        else:
            error = {"error_message": "Invalid parameters received"}
            return render(request, "error.tmpl", error)

        paginator = Paginator(qs, 100)
        page_number = request.GET.get("page")
        photos = paginator.get_page(page_number)
        information["media"] = photos

        return render(request, "search.tmpl", information)

    def post(self, request, *args, **kwargs):
        medium_id = request.POST["medium_id"]

        medium_id = medium_id.split(".")[0]

        medium_id = int(re.findall("\d+", medium_id)[0])

        try:
            medium = Medium.objects.get(id=medium_id)
        except ObjectDoesNotExist:
            template_information = {}
            template_information['medium_id_not_found'] = medium_id
            template_information['form_search_medium_id'] = MediumIdForm

            return render(request, "error_medium_id_not_found.tmpl", template_information)

        return redirect(reverse("medium", kwargs={"media_id": medium.pk}))


class DisplayRandom(TemplateView):
    def get(self, request, *args, **kwargs):
        type_of_medium = kwargs["type_of_medium"]

        qs = Medium.objects

        if type_of_medium == "photo":
            qs = qs.filter(medium_type=Medium.PHOTO)
            error_no_medium = {"error_message": "No photos available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
        elif type_of_medium == "video":
            qs = qs.filter(medium_type=Medium.VIDEO)
            error_no_medium = {"error_message": "No videos available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
        elif type_of_medium == "medium":
            qs = qs.all()
            error_no_medium = {"error_message": "No media available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
            pass

        if qs.count() == 0:
            return render(request, "error.tmpl", error_no_medium)

        qs = qs.order_by("?")

        return redirect(reverse("medium", kwargs={"media_id": qs[0].pk}))


def meters_to_degrees(meters):
    return meters / 40000000.0 * 360.0


class ListVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information["search_explanation"] = "Videos"

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by("file__object_storage_key")

        paginator = Paginator(videos_qs, 100)
        page_number = request.GET.get('page')
        videos = paginator.get_page(page_number)
        information['media'] = videos

        return render(request, "list_videos.tmpl", information)


class ListVideosExportCsv(TemplateView):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')

        response['Content-Disposition'] = 'attachment; filename="spi_search_videos-{}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by("file__object_storage_key")

        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Duration", "Link"])

        for video in videos_qs:
            absolute_link_to_medium_page = request.build_absolute_uri(reverse("medium", kwargs={"media_id": video.pk}))
            writer.writerow([video.pk, video.file.object_storage_key, video.duration_in_minutes_seconds(), absolute_link_to_medium_page])

        return response


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        context['medium'] = MediumForView.objects.get(id=kwargs['media_id'])

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


#     path('get/file/<str:md5>', GetPhoto.as_view())
class GetFile(View):
    def get(self, request, *args, **kwargs):
        bucket_name = request.GET['bucket']

        if bucket_name == "media":
            photo = Medium.objects.get(md5=kwargs['md5'])
        elif bucket_name == "resized":
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


class Stats(TemplateView):
    template_name = "stats.tmpl"

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        total_number_photos = Medium.objects.filter(medium_type=Medium.PHOTO).count()
        total_number_videos = Medium.objects.filter(medium_type=Medium.VIDEO).count()

        total_number_photos_resized = MediumResized.objects.filter(size_label="T").filter(medium__medium_type=Medium.PHOTO).count()
        total_number_videos_resized = MediumResized.objects.filter(size_label="L").filter(medium__medium_type=Medium.VIDEO).count()

        size_of_photos = Medium.objects.filter(medium_type=Medium.PHOTO).aggregate(Sum('file__size'))['file__size__sum']
        size_of_videos = Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('file__size'))['file__size__sum']
        size_of_videos_resized = MediumResized.objects.filter(size_label="L").filter(medium__medium_type="V").aggregate(Sum('medium__file__size'))['medium__file__size__sum']
        size_of_photos_resized = MediumResized.objects.filter(size_label="S").filter(medium__medium_type="P").aggregate(Sum('medium__file__size'))['medium__file__size__sum']

        if size_of_videos_resized is None:
            size_of_videos_resized = 0
        else:
            size_of_videos_resized = int(size_of_videos_resized)

        if size_of_photos_resized is None:
            size_of_photos_resized = 0
        else:
            size_of_photos_resized = int(size_of_photos_resized)


        duration_of_videos = utils.seconds_to_human_readable(Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('duration'))['duration__sum'])

        context['total_number_photos'] = total_number_photos
        context['total_number_videos'] = total_number_videos

        context['total_number_photos_resized'] = total_number_photos_resized
        context['total_number_videos_resized'] = total_number_videos_resized

        context['size_of_photos'] = utils.bytes_to_human_readable(size_of_photos)
        context['size_of_videos'] = utils.bytes_to_human_readable(size_of_videos)

        context['percentage_number_photos_resized'] = (total_number_photos_resized / total_number_photos) * 100.0
        context['percentage_number_videos_resized'] = (total_number_videos_resized / total_number_videos) * 100.0

        context['size_photos_resized'] = utils.bytes_to_human_readable(size_of_photos_resized)
        context['size_videos_resized'] = utils.bytes_to_human_readable(size_of_videos_resized)

        context['percentage_size_photos_resized'] = (size_of_photos_resized / size_of_photos) * 100.0
        context['percentage_size_videos_resized'] = (size_of_videos_resized / size_of_videos) * 100.0

        context['duration_videos'] = duration_of_videos

        return context
