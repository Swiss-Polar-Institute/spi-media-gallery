import csv
import datetime
import json
import os
import re
import urllib
from typing import Dict, List, Tuple, Union

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.gis.geos import GEOSGeometry, Point, Polygon
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.images import get_image_dimensions
from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import TemplateView, View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import utils
from .decorators import api_key_required
from .medium_for_view import MediumForView
from .models import (Copyright, File, License, Medium, MediumResized,
                     Photographer, RemoteMedium, TagName)
from .serializers import MediumDataSerializer, MediumSerializer
from .spi_s3_utils import SpiS3Utils
from .utils import percentage_of

from .forms import (  # isort:skip
    AddReferrerForm,
    MediaTypeForm,
    MediumIdForm,
    MultipleTagsSearchForm,
)

from django.http import (  # isort:skip
    HttpResponse,
    HttpResponseNotFound,
    JsonResponse,
    StreamingHttpResponse,
)


def create_dictionary_tag_name_to_id() -> Dict[str, str]:
    tag_name_to_id = {}

    for tag_name in TagName.objects.all():
        tag_name: TagName
        tag_name_to_id[tag_name.name] = tag_name.pk

    return tag_name_to_id


def get_tags_with_extra_information():
    tags = []

    last_indentation = 0
    name_to_id = create_dictionary_tag_name_to_id()

    for tag in TagName.objects.order_by("name"):
        t = {}

        tag_name = tag.name
        tag_indentation = tag_name.count("/")

        t["id"] = name_to_id.get(tag_name, None)

        if t["id"] is None:
            # A tag exists now but not when the dictionary was created
            continue

        t["open_uls"] = "<ul>" * (tag_indentation - last_indentation)
        t["close_uls"] = "</ul>" * (last_indentation - tag_indentation)

        last_indentation = tag_indentation

        t["tag"] = tag.name
        t["count"] = Medium.objects.filter(tags__name__name=tag_name).count()
        t["shortname"] = tag_name.split("/")[-1]

        tags.append(t)

    return tags


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


def search_for_nearby(
    latitude: float, longitude: float, km: float
) -> Tuple[Dict[str, str], object]:
    center_point: Point = Point(longitude, latitude, srid=4326)
    buffered: GEOSGeometry = center_point.buffer(meters_to_degrees(km * 1000))

    qs = MediumForView.objects.filter(location__within=buffered)

    if qs.count() != 1:
        media_string = "media"
    else:
        media_string = "medium"

    information = {}
    information[
        "search_query_human"
    ] = "{} radius of {} Km from latitude: {:.2f} longitude: {:.2f}".format(
        media_string, km, latitude, longitude
    )

    return information, qs


def search_in_box(
    north: float, south: float, east: float, west: float
) -> Tuple[Dict[str, str], object]:
    geom: Union[GEOSGeometry, Polygon] = Polygon.from_bbox((east, south, west, north))

    qs = MediumForView.objects.filter(location__contained=geom)

    information = {}

    information["search_query_human"] = "in area {:.2f} {:.2f} {:.2f} {:.2f}".format(
        north, east, south, west
    )

    return information, qs


def search_for_tag_name_ids(tag_name_ids: List[int]) -> Tuple[Dict[str, str], object]:
    information = {}

    qs = MediumForView.objects.order_by("datetime_taken")
    tags_list = []

    error = None
    for tag_name_id in tag_name_ids:
        try:
            tag_name_id_int = int(tag_name_id)
        except ValueError:
            error = "Invalid tag name id: {}".format(tag_name_id)
            break

        try:
            tag_name = TagName.objects.get(pk=tag_name_id_int).name
        except ObjectDoesNotExist:
            error = "Non-existing tag name id: {}".format(tag_name_id_int)
            break

        qs = qs.filter(tags__name__name=tag_name)
        tags_list.append(tag_name)

    if error is not None:
        qs = MediumForView.objects.none()
        tags_list = ["Error: Invalid tag name id"]

    tags_list = ", ".join(tags_list)

    if len(tag_name_ids) != 1:
        information["search_query_human"] = "tags: {}".format(tags_list)
    else:
        information["search_query_human"] = "tag: {}".format(tags_list)

    return information, qs


def add_filter_for_media_type(qs, media_type):
    if media_type == "P" or media_type == "V":
        qs = qs.filter(medium_type=media_type)

    return qs


def search_for_filenames(filename):
    information = {}

    qs = MediumForView.objects.filter(
        file__object_storage_key__icontains=filename
    ).order_by("file__object_storage_key")

    information["search_query_human"] = "media which filename contains: {}".format(
        filename
    )

    return information, qs


class Search(TemplateView):
    # @print_sql_decorator(count_only=False)
    def get(self, request, *args, **kwargs):
        if "tags" in request.GET:
            list_of_tag_ids = request.GET.getlist("tags")
            information, qs = search_for_tag_name_ids(list_of_tag_ids)

        elif "search_by_multiple_tags" in request.GET:
            list_of_tag_ids = []

            for key, value in request.GET.items():
                try:
                    tag_id = int(key)
                except ValueError:
                    continue

                if value == "on":
                    list_of_tag_ids.append(tag_id)

            information, qs = search_for_tag_name_ids(list_of_tag_ids)

        elif "filename" in request.GET:
            information, qs = search_for_filenames(request.GET["filename"])

        elif (
            "latitude" in request.GET
            and "longitude" in request.GET
            and "km" in request.GET
        ):
            latitude = float(request.GET["latitude"])
            longitude = float(request.GET["longitude"])
            km = float(request.GET["km"])

            information, qs = search_for_nearby(latitude, longitude, km)

        elif (
            "north" in request.GET
            and "south" in request.GET
            and "east" in request.GET
            and "west" in request.GET
        ):
            north = float(request.GET["north"])
            south = float(request.GET["south"])
            east = float(request.GET["east"])
            west = float(request.GET["west"])

            information, qs = search_in_box(north, south, east, west)

        elif "medium_id" in request.GET:
            medium_id = request.GET["medium_id"]
            medium_id = medium_id.split(".")[0]
            medium_id = re.findall(r"\d+", medium_id)

            if len(medium_id) != 1:
                template_information = {}
                template_information["medium_id_not_found"] = "Invalid Medium ID"
                template_information["form_search_medium_id"] = MediumIdForm

                return render(
                    request, "error_medium_id_not_found.tmpl", template_information
                )

            medium_id = int(medium_id[0])

            try:
                medium = Medium.objects.get(id=medium_id)
            except ObjectDoesNotExist:
                template_information = {}
                template_information["medium_id_not_found"] = medium_id
                template_information["form_search_medium_id"] = MediumIdForm

                return render(
                    request, "error_medium_id_not_found.tmpl", template_information
                )

            return redirect(reverse("medium", kwargs={"media_id": medium.pk}))

        else:
            error = {
                "error_message": "Invalid parameters. If searching by multiple tags, did you select at least one tag?"
            }
            return render(request, "error.tmpl", error, status=400)

        number_results_per_page = 100

        media_type_filter = request.GET.get("media_type", None)
        qs = add_filter_for_media_type(qs, media_type_filter)

        if media_type_filter == "P":
            information["search_query_human"] += " (only photos)"
        elif media_type_filter == "V":
            information["search_query_human"] += " (only videos)"

        paginator = Paginator(qs, number_results_per_page)

        try:
            page_number = int(request.GET.get("page", 1))
        except ValueError:
            page_number = 1

        media = paginator.get_page(page_number)
        information["media"] = media
        information["search_query"] = urllib.parse.quote_plus(
            request.META["QUERY_STRING"]
        )

        paginator_count = paginator.count

        if paginator_count <= number_results_per_page:
            information["current_results_information"] = "{} results".format(
                paginator_count
            )
        else:
            maximum_number = min(page_number * number_results_per_page, paginator_count)

            information["current_results_information"] = "{}-{} of {} results".format(
                (page_number - 1) * number_results_per_page + 1,
                maximum_number,
                paginator_count,
            )

        return render(request, "search.tmpl", information)


class DisplayRandom(TemplateView):
    def get(self, request, *args, **kwargs):
        type_of_medium = kwargs["type_of_medium"]

        qs = Medium.objects

        if type_of_medium == "photo":
            qs = qs.filter(medium_type=Medium.PHOTO)
            error_no_medium = {
                "error_message": "No photos available in this installation. Please contact {}".format(
                    settings.SITE_ADMINISTRATOR
                )
            }
        elif type_of_medium == "video":
            qs = qs.filter(medium_type=Medium.VIDEO)
            error_no_medium = {
                "error_message": "No videos available in this installation. Please contact {}".format(
                    settings.SITE_ADMINISTRATOR
                )
            }
        elif type_of_medium == "medium":
            qs = qs.all()
            error_no_medium = {
                "error_message": "No media available in this installation. Please contact {}".format(
                    settings.SITE_ADMINISTRATOR
                )
            }
        else:
            error_no_medium = {"error_message": "Invalid type of medium"}
            qs = []

        if qs.count() == 0:
            return render(request, "error.tmpl", error_no_medium)

        qs = qs.order_by("?")

        return redirect(reverse("medium", kwargs={"media_id": qs[0].pk}))


def meters_to_degrees(meters: float) -> float:
    return meters / 40000000.0 * 360.0


class ListVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information["search_explanation"] = "Videos"

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by(
            "file__object_storage_key"
        )

        paginator = Paginator(videos_qs, 100)
        page_number = request.GET.get("page")
        videos = paginator.get_page(page_number)
        information["media"] = videos

        return render(request, "list_videos.tmpl", information)


class ListVideosExportCsv(TemplateView):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")

        response[
            "Content-Disposition"
        ] = "attachment; filename='spi_search_videos-{}.csv'".format(
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        )

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by(
            "file__object_storage_key"
        )

        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Duration", "Link"])

        for video in videos_qs:
            absolute_link_to_medium_page = request.build_absolute_uri(
                reverse("medium", kwargs={"media_id": video.pk})
            )
            writer.writerow(
                [
                    video.pk,
                    video.file.object_storage_key,
                    video.duration_in_minutes_seconds(),
                    absolute_link_to_medium_page,
                ]
            )

        return response


class Display(TemplateView):
    def get(self, request, *args, **kwargs):
        try:
            medium = MediumForView.objects.get(id=kwargs["media_id"])
        except ObjectDoesNotExist:
            error = {"error_message": "Media not found"}
            return render(request, "error.tmpl", error, status=404)

        search_query = request.GET.get("search_query", None)
        return render(
            request, "display.tmpl", {"medium": medium, "search_query": search_query}
        )


class Map(TemplateView):
    template_name = "map.tmpl"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class PhotosGeojson(View):
    def get(self, request):
        serialized = serialize(
            "geojson", Medium.objects.all(), geometry_field="location", fields=("pk",)
        )
        return JsonResponse(json.loads(serialized))


class TrackGeojson(View):
    def get(self, request_):
        track = open(settings.TRACK_MAP_FILEPATH, "r")
        return JsonResponse(json.load(track))


class GetFile(View):
    def get(self, request, *args, **kwargs):
        bucket_name = kwargs["bucket_name"]
        md5 = kwargs["md5"]

        content_type = request.GET["content_type"]
        content_disposition_type = request.GET["content_disposition_type"]
        filename = request.GET["filename"]

        try:
            file = File.objects.filter(md5=md5, bucket=bucket_name)[0]
        except IndexError:
            return HttpResponseNotFound("File not found")

        spi_s3 = SpiS3Utils(file.bucket_name())

        url = spi_s3.get_presigned_link(
            file.object_storage_key, content_disposition_type, content_type, filename
        )

        r = requests.get(url=url, stream=True)
        r.raise_for_status()

        response = StreamingHttpResponse(r.raw, content_type=content_type)
        response["Content-Length"] = str(file.size)
        response["Content-Disposition"] = "{}; filename={}".format(
            content_disposition_type, filename
        )
        return response


class SearchByMultipleTags(TemplateView):
    template_name = "search_by_multiple_tags.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tags = get_tags_with_extra_information()

        context["form_search_by_multiple_tags"] = MultipleTagsSearchForm(tags=tags)
        context["media_type_form"] = MediaTypeForm
        context["add_referrer_form"] = AddReferrerForm(
            referrer="search_by_multiple_tags"
        )

        return context


class Stats(TemplateView):
    template_name = "stats.tmpl"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_number_photos = Medium.objects.filter(medium_type=Medium.PHOTO).count()
        total_number_videos = Medium.objects.filter(medium_type=Medium.VIDEO).count()

        total_number_photos_resized = (
            MediumResized.objects.filter(size_label="T")
            .filter(medium__medium_type=Medium.PHOTO)
            .count()
        )
        total_number_videos_resized = (
            MediumResized.objects.filter(size_label="L")
            .filter(medium__medium_type=Medium.VIDEO)
            .count()
        )

        size_of_photos = Medium.objects.filter(medium_type=Medium.PHOTO).aggregate(
            Sum("file__size")
        )["file__size__sum"]
        size_of_videos = Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(
            Sum("file__size")
        )["file__size__sum"]
        size_of_videos_resized = (
            MediumResized.objects.filter(size_label="L")
            .filter(medium__medium_type="V")
            .aggregate(Sum("medium__file__size"))["medium__file__size__sum"]
        )
        size_of_photos_resized = (
            MediumResized.objects.filter(size_label="S")
            .filter(medium__medium_type="P")
            .aggregate(Sum("medium__file__size"))["medium__file__size__sum"]
        )

        if size_of_videos_resized is None:
            size_of_videos_resized = 0
        else:
            size_of_videos_resized = int(size_of_videos_resized)

        if size_of_photos_resized is None:
            size_of_photos_resized = 0
        else:
            size_of_photos_resized = int(size_of_photos_resized)

        duration_of_videos = utils.seconds_to_human_readable(
            Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum("duration"))[
                "duration__sum"
            ]
        )

        context["total_number_photos"] = total_number_photos
        context["total_number_videos"] = total_number_videos

        context["total_number_photos_resized"] = total_number_photos_resized
        context["total_number_videos_resized"] = total_number_videos_resized

        context["size_of_photos"] = utils.bytes_to_human_readable(size_of_photos)
        context["size_of_videos"] = utils.bytes_to_human_readable(size_of_videos)

        context["percentage_number_photos_resized"] = percentage_of(
            total_number_photos_resized, total_number_photos
        )
        context["percentage_number_videos_resized"] = percentage_of(
            total_number_videos_resized, total_number_videos
        )

        context["size_photos_resized"] = utils.bytes_to_human_readable(
            size_of_photos_resized
        )
        context["size_videos_resized"] = utils.bytes_to_human_readable(
            size_of_videos_resized
        )

        context["percentage_size_photos_resized"] = percentage_of(
            size_of_photos_resized, size_of_photos
        )
        context["percentage_size_videos_resized"] = percentage_of(
            size_of_videos_resized, size_of_videos
        )

        context["duration_videos"] = duration_of_videos

        context[
            "total_number_media_from_project_application"
        ] = RemoteMedium.objects.count()

        if context["total_number_media_from_project_application"] > 0:
            context[
                "latest_photo_imported_from_project_application"
            ] = RemoteMedium.objects.latest("remote_modified_on").remote_modified_on
        else:
            context["latest_photo_imported_from_project_application"] = "N/A"

        return context


class ImportFromProjectApplicationCallback(View):
    @api_key_required
    def get(self, request):
        # Testing - testing code
        # This is a test function - avoid doing this
        # Celery seems the way to go or some other way to launch jobs and get results
        # This can take long time so it cannot be processed in the view (e.g. download and resize a video)
        os.system("python3 manage.py import_from_project_application &")

        return JsonResponse(status=200, data={"status": "ok"})


class MediumUploadView(APIView):
    def post(self, request):
        request.data._mutable = True
        if "file" in request.data:
            medium_file = request.data["file"]

            spi_s3 = SpiS3Utils(bucket_name="imported")
            spi_s3.put_object(medium_file.name, medium_file)

            file = File()
            file.object_storage_key = medium_file.name
            file.md5 = utils.hash_of_file(medium_file)
            file.size = medium_file.size
            file.bucket = File.IMPORTED
            file.save()
            request.data["file"] = file.pk
            width, height = get_image_dimensions(medium_file)
            request.data["height"] = height
            request.data["width"] = width
        tags = []
        if "people" in request.data:
            tags.append(request.data["people"])
        if "location_value" in request.data:
            tags.append(request.data["location_value"])
        if "project" in request.data:
            tags.append(request.data["project"])
        request.data["tags"] = tags
        serializer = MediumSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SelectionView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":

            if "orderby" in request.GET:
                order_by_text = request.GET.get("orderby")
                qs = MediumForView.objects.filter(is_image_of_the_week=True).order_by(order_by_text)
                if "archive_type" in request.GET:
                    archive_type = request.GET.get("archive_type")
                    if archive_type != "":
                        qs = MediumForView.objects.filter(is_image_of_the_week=True, is_archive=archive_type).order_by(order_by_text)
                qs_count = qs.count()
                number_results_per_page = 15
                paginator = Paginator(qs, number_results_per_page)
                try:
                    page_number = int(request.GET.get("page", 1))
                except ValueError:
                    page_number = 1
                medium = paginator.get_page(page_number)
                html = render_to_string("filter_projects.tmpl", {"medium": medium})

            if "page" in request.GET:
                page = int(request.GET.get("page", None))
                number_results_per_page = 15
                starting_number = (page - 1) * number_results_per_page
                ending_number = page * number_results_per_page
                qs = MediumForView.objects.filter(is_image_of_the_week=True)
                qs_count = qs.count()
                page_number = page + 1
                qs = qs[starting_number:ending_number]

                html = render_to_string("filter_projects.tmpl", {"medium": qs})

            return HttpResponse(
                json.dumps(
                    {"html": html, "count": qs_count, "page_number": page_number}
                ),
                content_type="application/json",
            )

        try:
            qs = MediumForView.objects.filter(is_image_of_the_week=True)
            count = qs.count()
            locations = TagName.objects.filter(name__icontains="location")
            projects = TagName.objects.filter(name__icontains="spi project")
            photographers = TagName.objects.filter(name__icontains="photographer")
            peoples = TagName.objects.filter(name__icontains="people")
            number_results_per_page = 15
            paginator = Paginator(qs, number_results_per_page)
            try:
                page_number = int(request.GET.get("page", 1))
            except ValueError:
                page_number = 1
            medium = paginator.get_page(page_number)

        except ObjectDoesNotExist:
            error = {"error_message": "Media not found"}
            return render(request, "error.tmpl", error, status=404)

        search_query = request.GET.get("search_query", None)
        return render(
            request,
            "selection.tmpl",
            {
                "medium": medium,
                "search_query": search_query,
                "locations": locations,
                "projects": projects,
                "photographers": photographers,
                "peoples": peoples,
                "count": count,
            },
        )

    def post(self, request):
        id = request.POST["fileid"]
        title = request.POST["title"]
        image_desc = request.POST["image_desc"]
        order = request.POST["order"]
        if 'is_archive' in request.POST:
            is_archive = request.POST['is_archive']
        else:
            is_archive = False
        medium = Medium.objects.get(id=id)
        medium.title = title
        medium.image_desc = image_desc
        medium.order = order
        medium.is_archive = is_archive
        medium.save()
        messages.success(request, "Changes successfully saved.")
        return redirect("/selection")


class MediumView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            list_of_tag_ids = []
            if "project_id" in request.GET:
                project_id = request.GET.get("project_id")
                list_of_tag_ids.append(project_id)
            if "location_id" in request.GET:
                location_id = request.GET.get("location_id")
                list_of_tag_ids.append(location_id)
            if "photographer_id" in request.GET:
                photographer_id = request.GET.get("photographer_id")
                list_of_tag_ids.append(photographer_id)
            if "people_id" in request.GET:
                people_id = request.GET.get("people_id")
                list_of_tag_ids.append(people_id)
            if "is_image_of_the_week" in request.GET:
                is_image_of_the_week = request.GET.get("is_image_of_the_week")
                id = request.GET.get("id")
                medium = Medium.objects.get(id=id)
                medium.is_image_of_the_week = is_image_of_the_week
                medium.save()

            information, qs = search_for_tag_name_ids(list_of_tag_ids)
            qs_count = qs.count()
            number_results_per_page = 15
            paginator = Paginator(qs, number_results_per_page)
            try:
                page_number = int(request.GET.get("page", 1))
            except ValueError:
                page_number = 1
            medium = paginator.get_page(page_number)
            html = render_to_string("filter_projects_medium.tmpl", {"medium": medium})

            if "orderby" in request.GET:
                order_by_text = request.GET.get("orderby")
                qs = MediumForView.objects.order_by(order_by_text)
                qs_count = qs.count()
                number_results_per_page = 15
                paginator = Paginator(qs, number_results_per_page)
                try:
                    page_number = int(request.GET.get("page", 1))
                except ValueError:
                    page_number = 1
                medium = paginator.get_page(page_number)
                html = render_to_string(
                    "filter_projects_medium.tmpl", {"medium": medium}
                )

            if "page" in request.GET:
                page = int(request.GET.get("page", None))
                number_results_per_page = 15
                starting_number = (page - 1) * number_results_per_page
                ending_number = page * number_results_per_page
                qs = MediumForView.objects.order_by("datetime_taken")
                qs_count = qs.count()
                page_number = page + 1
                information, qs = search_for_tag_name_ids(list_of_tag_ids)
                qs = qs[starting_number:ending_number]

                html = render_to_string("filter_projects_medium.tmpl", {"medium": qs})

            return HttpResponse(
                json.dumps(
                    {"html": html, "count": qs_count, "page_number": page_number}
                ),
                content_type="application/json",
            )

        try:
            qs = MediumForView.objects.order_by("datetime_taken")
            count = qs.count()
            locations = TagName.objects.filter(name__icontains="location")
            projects = TagName.objects.filter(name__icontains="spi project")
            photographers = TagName.objects.filter(name__icontains="photographer")
            peoples = TagName.objects.filter(name__icontains="people")
            number_results_per_page = 15
            paginator = Paginator(qs, number_results_per_page)
            try:
                page_number = int(request.GET.get("page", 1))
            except ValueError:
                page_number = 1
            medium = paginator.get_page(page_number)

        except ObjectDoesNotExist:
            error = {"error_message": "Media not found"}
            return render(request, "error.tmpl", error, status=404)

        search_query = request.GET.get("search_query", None)
        return render(
            request,
            "medium.tmpl",
            {
                "medium": medium,
                "search_query": search_query,
                "locations": locations,
                "projects": projects,
                "photographers": photographers,
                "peoples": peoples,
                "count": count,
            },
        )


def SearchAll(request):
    if "page" in request.GET:
        page = int(request.GET.get("page", None))
        search_term = request.GET.get("search_term", None)
        number_results_per_page = 12
        starting_number = (page - 1) * number_results_per_page
        ending_number = page * number_results_per_page
        qs = (
            MediumForView.objects.filter(
                photographer__first_name__icontains=search_term
            )
            | MediumForView.objects.filter(
                photographer__last_name__icontains=search_term
            )
            | MediumForView.objects.filter(location__icontains=search_term)
            | MediumForView.objects.filter(
                copyright__public_text__icontains=search_term
            )
        )
        qs_count = qs.count()
        page_number = page + 1
        qs = qs[starting_number:ending_number]
        html = render_to_string("filter_search_results.tmpl", {"media": qs})
        return HttpResponse(
            json.dumps(
                {
                    "html": html,
                    "count": qs_count,
                    "page_number": page_number,
                    "search_term": search_term,
                }
            ),
            content_type="application/json",
        )
    search_term = request.POST["search_term"]
    qs = (
        MediumForView.objects.filter(photographer__first_name__icontains=search_term)
        | MediumForView.objects.filter(photographer__last_name__icontains=search_term)
        | MediumForView.objects.filter(location__icontains=search_term)
        | MediumForView.objects.filter(copyright__public_text__icontains=search_term)
    )
    count = qs.count()
    number_results_per_page = 12
    paginator = Paginator(qs, number_results_per_page)
    try:
        page_number = int(request.GET.get("page", 1))
    except ValueError:
        page_number = 1
    medium = paginator.get_page(page_number)
    return render(
        request,
        "search_results.tmpl",
        {"media": medium, "count": count, "search_term": search_term},
    )


class MediumList(APIView):
    def get(self, request):
        qs = MediumForView.objects.filter(is_image_of_the_week=True, is_archive=False).order_by('-order')
        serializer = MediumDataSerializer(qs, many=True)
        return Response(serializer.data)


class MediumBanner(APIView):
    def get(self, request):
        qs = MediumForView.objects.filter(is_image_of_the_week=True, medium_type="P")
        serializer = MediumDataSerializer(qs, many=True)
        return Response(serializer.data)


def get_copyright_list(request):
    copyright_list = Copyright.objects.all()
    return {"copyrights": copyright_list}


def get_license_list(request):
    license_list = License.objects.all()
    return {"license_list": license_list}


def get_photographer_list(request):
    photographer_list = Photographer.objects.all()
    return {"photographers_list": photographer_list}
