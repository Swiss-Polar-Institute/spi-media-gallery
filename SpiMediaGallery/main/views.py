import csv
import datetime
import json
import re
import urllib
from typing import Dict, Tuple, Union, List

import requests
from django.conf import settings
from django.contrib.gis.geos import Point, Polygon, GEOSGeometry
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView, View

from . import utils
from .forms import MediumIdForm, FileNameForm
from .medium_for_view import MediumForView
from .models import Medium, MediumResized, TagName, File
from .spi_s3_utils import SpiS3Utils


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

    for tag in TagName.objects.order_by('name'):
        t = {}

        tag_name = tag.name
        tag_indentation = tag_name.count('/')

        t['id'] = name_to_id.get(tag_name, None)

        if t['id'] is None:
            # A tag exists now but not when the dictionary was created
            continue

        t['open_uls'] = '<ul>' * (tag_indentation - last_indentation)
        t['close_uls'] = '</ul>' * (last_indentation - tag_indentation)

        last_indentation = tag_indentation

        t['tag'] = tag.name
        t['count'] = Medium.objects.filter(tags__name__name=tag_name).count()
        t['shortname'] = tag_name.split('/')[-1]

        tags.append(t)

    return tags


class Homepage(TemplateView):
    template_name = 'homepage.tmpl'

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        list_of_tags = get_tags_with_extra_information()

        if len(list_of_tags) > 0:
            context['close_orphaned_uls'] = '</ul>' * list_of_tags[-1]['tag'].count('/')
        else:
            context['closed_orphaned_uls'] = ''

        context['list_of_tags'] = list_of_tags
        context['form_search_medium_id'] = MediumIdForm
        context['form_search_file_name'] = FileNameForm

        return context


def search_for_nearby(latitude: float, longitude: float, km: float) -> Tuple[Dict[str, str], object]:
    center_point: Point = Point(longitude, latitude, srid=4326)
    buffered: GEOSGeometry = center_point.buffer(meters_to_degrees(km * 1000))

    qs = MediumForView.objects.filter(location__within=buffered)

    if qs.count() != 1:
        media_string = 'media'
    else:
        media_string = 'medium'

    information = {}
    information['search_query_human'] = 'radius of {} Km from latitude: {:.2f} longitude: {:.2f}'.format(
        media_string, km, latitude, longitude)

    return information, qs


def search_in_box(north: float, south: float, east: float, west: float) -> Tuple[Dict[str, str], object]:
    geom: Union[GEOSGeometry, Polygon] = Polygon.from_bbox((east, south, west, north))

    qs = MediumForView.objects.filter(location__contained=geom)

    information = {}

    information['search_query_human'] = 'in area {:.2f} {:.2f} {:.2f} {:.2f}'.format(
        north, east,
        south, west)

    return information, qs


def search_for_tag_ids(tag_ids: [List[int]]) -> Union[Dict[str, str], object]:
    information = {}

    qs = MediumForView.objects.order_by('datetime_taken')
    tags_list = []

    for tag_id in tag_ids:
        tag_name = TagName.objects.get(pk=tag_id).name

        qs = qs.filter(tags__name__name=tag_name)
        tags_list.append(tag_name)

    tags_list = ', '.join(tags_list)

    if len(tag_ids) != 1:
        information['search_query_human'] = 'tags: {}'.format(tags_list)
    else:
        information['search_query_human'] = 'tag: {}'.format(tags_list)

    return information, qs


def search_for_filenames(filename):
    information = {}

    qs = MediumForView.objects.filter(file__object_storage_key__icontains=filename).order_by('file__object_storage_key')

    information['search_query_human'] = 'media which filename contains: {}'.format(filename)

    return information, qs


class Search(TemplateView):
    # @print_sql_decorator(count_only=False)
    def get(self, request, *args, **kwargs):
        if 'tags' in request.GET:
            list_of_tag_ids = request.GET.getlist('tags')
            information, qs = search_for_tag_ids(list_of_tag_ids)

        elif 'filename' in request.GET:
            information, qs = search_for_filenames(request.GET['filename'])

        elif 'latitude' in request.GET and 'longitude' in request.GET and 'km' in request.GET:
            latitude = float(request.GET['latitude'])
            longitude = float(request.GET['longitude'])
            km = float(request.GET['km'])

            information, qs = search_for_nearby(latitude, longitude, km)

        elif 'north' in request.GET and 'south' in request.GET and 'east' in request.GET and 'west' in request.GET:
            north = float(request.GET['north'])
            south = float(request.GET['south'])
            east = float(request.GET['east'])
            west = float(request.GET['west'])

            information, qs = search_in_box(north, south, east, west)

        elif 'medium_id' in request.GET:
            medium_id = request.GET['medium_id']
            medium_id = medium_id.split('.')[0]
            medium_id = re.findall('\d+', medium_id)

            if len(medium_id) != 1:
                template_information = {}
                template_information['medium_id_not_found'] = 'Invalid Medium ID'
                template_information['form_search_medium_id'] = MediumIdForm

                return render(request, 'error_medium_id_not_found.tmpl', template_information)

            medium_id = int(medium_id[0])

            try:
                medium = Medium.objects.get(id=medium_id)
            except ObjectDoesNotExist:
                template_information = {}
                template_information['medium_id_not_found'] = medium_id
                template_information['form_search_medium_id'] = MediumIdForm

                return render(request, 'error_medium_id_not_found.tmpl', template_information)

            return redirect(reverse('medium', kwargs={'media_id': medium.pk}))

        else:
            error = {'error_message': 'Invalid parameters received. If searching by multiple tags, did you select at least one tag?'}
            return render(request, 'error.tmpl', error, status=400)

        number_results_per_page = 100
        paginator = Paginator(qs, number_results_per_page)

        try:
            page_number = int(request.GET.get('page', 1))
        except ValueError:
            page_number = 1

        photos = paginator.get_page(page_number)
        information['media'] = photos
        information['search_query'] = urllib.parse.quote_plus(request.META['QUERY_STRING'])

        paginator_count = paginator.count

        if paginator_count <= number_results_per_page:
            information['current_results_information'] = '{} results'.format(paginator_count)
        else:
            maximum_number = min(page_number*number_results_per_page, paginator_count)

            information['current_results_information'] = '{}-{} of {} results'.format((page_number-1)*number_results_per_page+1,
                                                                              maximum_number,
                                                                              paginator_count)

        return render(request, 'search.tmpl', information)


class DisplayRandom(TemplateView):
    def get(self, request, *args, **kwargs):
        type_of_medium = kwargs['type_of_medium']

        qs = Medium.objects

        if type_of_medium == 'photo':
            qs = qs.filter(medium_type=Medium.PHOTO)
            error_no_medium = {'error_message': 'No photos available in this installation. Please contact {}'.format(
                settings.SITE_ADMINISTRATOR)}
        elif type_of_medium == 'video':
            qs = qs.filter(medium_type=Medium.VIDEO)
            error_no_medium = {'error_message': 'No videos available in this installation. Please contact {}'.format(
                settings.SITE_ADMINISTRATOR)}
        elif type_of_medium == 'medium':
            qs = qs.all()
            error_no_medium = {'error_message': 'No media available in this installation. Please contact {}'.format(
                settings.SITE_ADMINISTRATOR)}
        else:
            error_no_medium = {'error_message': 'Invalid type of medium'}
            qs = []

        if qs.count() == 0:
            return render(request, 'error.tmpl', error_no_medium)

        qs = qs.order_by('?')

        return redirect(reverse('medium', kwargs={'media_id': qs[0].pk}))


def meters_to_degrees(meters: float) -> float:
    return meters / 40000000.0 * 360.0


class ListVideos(TemplateView):
    def get(self, request, *args, **kwargs):
        information = {}

        information['search_explanation'] = 'Videos'

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by('file__object_storage_key')

        paginator = Paginator(videos_qs, 100)
        page_number = request.GET.get('page')
        videos = paginator.get_page(page_number)
        information['media'] = videos

        return render(request, 'list_videos.tmpl', information)


class ListVideosExportCsv(TemplateView):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')

        response['Content-Disposition'] = "attachment; filename='spi_search_videos-{}.csv'".format(
            datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

        videos_qs = MediumForView.objects.filter(medium_type=Medium.VIDEO).order_by('file__object_storage_key')

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Duration', 'Link'])

        for video in videos_qs:
            absolute_link_to_medium_page = request.build_absolute_uri(reverse('medium', kwargs={'media_id': video.pk}))
            writer.writerow([video.pk, video.file.object_storage_key, video.duration_in_minutes_seconds(),
                             absolute_link_to_medium_page])

        return response


class Display(TemplateView):
    def get(self, request, *args, **kwargs):
        try:
            medium = MediumForView.objects.get(id=kwargs['media_id'])
        except ObjectDoesNotExist:
            error = {'error_message': 'Media not found'}
            return render(request, 'error.tmpl', error, status=404)

        search_query = request.GET.get('search_query', None)
        return render(request, 'display.tmpl', {'medium': medium, 'search_query': search_query})


class Map(TemplateView):
    template_name = 'map.tmpl'

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        return context


class PhotosGeojson(View):
    def get(self, request):
        serialized = serialize('geojson', Medium.objects.all(), geometry_field='location', fields=('pk',))
        return JsonResponse(json.loads(serialized))


class TrackGeojson(View):
    def get(self, request_):
        track = open(settings.TRACK_MAP_FILEPATH, 'r')
        return JsonResponse(json.load(track))


class GetFile(View):
    def get(self, request, *args, **kwargs):
        bucket_name = kwargs['bucket_name']
        md5 = kwargs['md5']

        content_type = request.GET['content_type']
        content_disposition_type = request.GET['content_disposition_type']
        filename = request.GET['filename']

        try:
            file = File.objects.get(md5=md5, bucket=bucket_name)
        except ObjectDoesNotExist:
            return HttpResponseNotFound('File not found')

        spi_s3 = SpiS3Utils(file.bucket_name())

        url = spi_s3.get_presigned_link(file.object_storage_key, content_disposition_type, content_type, filename)

        r = requests.get(url=url, stream=True)
        r.raise_for_status()

        response = HttpResponse(r.raw, content_type=content_type)
        response['Content-Disposition'] = '{}; filename={}'.format(content_disposition_type, filename)
        return response


class SearchByMultipleTags(TemplateView):
    template_name = 'search_by_multiple_tags.html'

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        tags = get_tags_with_extra_information()

        context['list_of_tags_first_half'] = tags[:int(1 + len(tags) / 2)]
        context['list_of_tags_second_half'] = tags[int(1 + len(tags) / 2):]

        return context


class Stats(TemplateView):
    template_name = 'stats.tmpl'

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)

        total_number_photos = Medium.objects.filter(medium_type=Medium.PHOTO).count()
        total_number_videos = Medium.objects.filter(medium_type=Medium.VIDEO).count()

        total_number_photos_resized = MediumResized.objects.filter(size_label='T').filter(
            medium__medium_type=Medium.PHOTO).count()
        total_number_videos_resized = MediumResized.objects.filter(size_label='L').filter(
            medium__medium_type=Medium.VIDEO).count()

        size_of_photos = Medium.objects.filter(medium_type=Medium.PHOTO).aggregate(Sum('file__size'))['file__size__sum']
        size_of_videos = Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('file__size'))['file__size__sum']
        size_of_videos_resized = MediumResized.objects.filter(size_label='L').filter(medium__medium_type='V').aggregate(
            Sum('medium__file__size'))['medium__file__size__sum']
        size_of_photos_resized = MediumResized.objects.filter(size_label='S').filter(medium__medium_type='P').aggregate(
            Sum('medium__file__size'))['medium__file__size__sum']

        if size_of_videos_resized is None:
            size_of_videos_resized = 0
        else:
            size_of_videos_resized = int(size_of_videos_resized)

        if size_of_photos_resized is None:
            size_of_photos_resized = 0
        else:
            size_of_photos_resized = int(size_of_photos_resized)

        duration_of_videos = utils.seconds_to_human_readable(
            Medium.objects.filter(medium_type=Medium.VIDEO).aggregate(Sum('duration'))['duration__sum'])

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
