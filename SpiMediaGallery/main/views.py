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

        total_photos = Medium.objects.filter(medium_type=Medium.PHOTO).count()
        total_videos = Medium.objects.filter(medium_type=Medium.VIDEO).count()

        total_photo_thumbnails = MediumResized.objects.filter(size_label="T").filter(medium__medium_type=Medium.PHOTO).count()
        total_video_thumbnails = MediumResized.objects.filter(size_label="S").filter(medium__medium_type=Medium.VIDEO).count()

        size_of_photos = Medium.objects.filter(medium_type=Medium.PHOTO).aggregate(Sum('file_size'))['file_size__sum']
        size_of_videos = Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('file_size'))['file_size__sum']
        size_of_videos_already_resized = int(MediumResized.objects.filter(size_label="S").filter(medium__medium_type="V").aggregate(Sum('medium__file_size'))['medium__file_size__sum'])

        duration_of_videos = utils.seconds_to_human_readable(Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('duration'))['duration__sum'])

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

        context['size_of_photos'] = utils.bytes_to_human_readable(size_of_photos)
        context['size_of_videos'] = utils.bytes_to_human_readable(size_of_videos)
        context['percentage_already_resized'] = (size_of_videos_already_resized / size_of_videos) * 100.0

        context['duration_videos'] = duration_of_videos

        context['list_of_tags'] = tags

        context['list_of_tags_first_half'] = tags[:int(1+len(tags)/2)]
        context['list_of_tags_second_half'] = tags[int(1+len(tags)/2):]

        context['form_search_medium_id'] = MediumIdForm

        return context


def information_for_tag_ids(tag_ids):
    information = {}

    query_photos_for_tags = MediumForView.objects.order_by("datetime_taken")
    tags_list = []

    for tag_id in tag_ids:
        query_photos_for_tags = query_photos_for_tags.filter(tags__id=int(tag_id))
        tags_list.append(Tag.objects.get(id=tag_id).tag)

    tags_list = ", ".join(tags_list) # Tag.objects.get(id=kwargs["tag_id"])

    if len(query_photos_for_tags) != 1:
        photos_string = "Media"
    else:
        photos_string = "Medium"

    if len(tag_ids) != 1:
        information["search_explanation"] = "{} {} with these tags: {}".format(len(query_photos_for_tags), photos_string, tags_list)
    else:
        information["search_explanation"] = "{} {} with this tag: {}".format(len(query_photos_for_tags), photos_string, tags_list)

    information["photos_qs"] = query_photos_for_tags

    return information


class SearchMultipleTags(TemplateView):
    def get(self, request, *args, **kwargs):
        list_of_tag_ids = request.GET.getlist('tags')

        information = information_for_tag_ids(list_of_tag_ids)

        paginator = Paginator(information["photos_qs"], 200)

        page = request.GET.get("page")

        photos = paginator.get_page(page)

        information["media"] = photos

        return render(request, "search.tmpl", information)


class RandomPhoto(TemplateView):
    def get(self, request, *args, **kwargs):
        random_photos = Medium.objects.filter(medium_type=Medium.PHOTO).order_by('?')

        if len(random_photos) == 0:
            information = {"error_message": "No photos available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
            return render(request, "error.tmpl", information)

        random_photo = random_photos[0]

        return redirect("/display/{}".format(random_photo.id))


class RandomVideo(TemplateView):
    def get(self, request, *args, **kwargs):
        random_videos = Medium.objects.filter(medium_type=Medium.VIDEO).order_by('?')

        if len(random_videos) == 0:
            information = {"error_message": "No videos available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
            return render(request, "error.tmpl", information)

        random_video = random_videos[0]

        return redirect("/display/{}".format(random_video.id))


class RandomMedium(TemplateView):
    def get(self, request, *args, **kwargs):
        random_media = Medium.objects.all().order_by('?')

        if len(random_media) == 0:
            information = {"error_message": "No media available in this installation. Please contact {}".format(settings.SITE_ADMINISTRATOR)}
            return render(request, "error.tmpl", information)

        random_medium = random_media[0]

        return redirect("/display/{}".format(random_medium.id))


class SearchMediumId(TemplateView):
    def post(self, request, *args, **kwargs):
        medium_id = request.POST["medium_id"]

        medium_id = medium_id.split(".")[0]

        medium_id = int(re.findall("\d+", medium_id)[0])

        try:
            photo = Medium.objects.get(id=medium_id)
        except ObjectDoesNotExist:
            template_information = {}
            template_information['medium_id_not_found'] = medium_id
            template_information['form_search_medium_id'] = MediumIdForm

            return render(request, "error_medium_id_not_found.tmpl", template_information)

        return redirect("/display/{}".format(photo.id))


class SearchBox(TemplateView):
    def get(self, request, *args, **kwargs):
        north = float(request.GET["north"])
        south = float(request.GET["south"])
        east = float(request.GET["east"])
        west = float(request.GET["west"])

        information = {}

        geom = Polygon.from_bbox((east, south, west, north))

        query_media_in_geom = MediumForView.objects.filter(location__contained=geom)

        if len(query_media_in_geom) != 1:
            photos_string = "photos"
        else:
            photos_string = "photo"

        information["search_explanation"] = "{} {} taken in area {:.2f} {:.2f} {:.2f} {:.2f}".format(len(query_media_in_geom),
                                                                                                     photos_string,
                                                                                                     north, east,
                                                                                                     south, west)

        information["media"] = query_media_in_geom

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

        query_media_nearby = MediumForView.objects.filter(location__within=buffered)

        if len(query_media_nearby) != 1:
            photos_string = "media"
        else:
            photos_string = "medium"

        information = {}
        information["search_explanation"] = "{} {} in a radius of {} Km from latitude: {:.2f} longitude: {:.2f}".format(len(query_media_nearby),
                                                                                                                        photos_string, km, latitude, longitude)
        paginator = Paginator(query_media_nearby, 100)

        page = request.GET.get('page')

        paginated = paginator.get_page(page)

        information['media'] = paginated

        return render(request, "search.tmpl", information)


class SearchVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information["search_explanation"] = "Videos"

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by("object_storage_key")

        paginator = Paginator(videos_qs, 100)

        page = request.GET.get('page')

        videos = paginator.get_page(page)

        information['media'] = videos

        return render(request, "search_videos.tmpl", information)


class SearchVideosExportCsv(TemplateView):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')

        response['Content-Disposition'] = 'attachment; filename="spi_search_videos-{}.csv"'.format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by("object_storage_key")

        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Duration", "Link"])

        for video in videos_qs:
            writer.writerow([video.pk, video.object_storage_key, video.duration_in_minutes_seconds(), request.build_absolute_uri("/display/{}".format(video.pk))])

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
