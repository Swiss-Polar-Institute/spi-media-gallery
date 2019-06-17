from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView
from main.models import Photo, Tag

import boto3


class Homepage(TemplateView):
    template_name = "homepage.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Homepage, self).get_context_data(**kwargs)

        total_photos = Photo.objects.count()
        total_thumbnails = Photo.objects.filter(thumbnail__isnull=False).count()
        tags = Tag.objects.order_by("tag")

        context['total_number_photos'] = total_photos
        context['total_number_thumbnails'] = total_thumbnails
        context['list_of_tags'] = tags

        return context


class SearchResult(TemplateView):
    template_name = "search_result.tmpl"

    def get_context_data(self, **kwargs):
        r = boto3.resource(service_name="s3",
                       aws_access_key_id="minio",
                       aws_secret_access_key="minio123",
                       endpoint_url="http://localhost:9000")

        s3_file_path = r.meta.client.generate_presigned_url('get_object',
                                              Params={'Bucket': 'thumbnails',
                                                      'Key': '03e3c8f280b2f491f58be4b5ff6d0cb5-thumbnail.jpg',
                                                      'ResponseContentType': 'image/jpeg'})


        print(s3_file_path)

        # bucket = r.get_bucket('thumbnails')
        # s3_file_path = bucket.get_key('03e3c8f280b2f491f58be4b5ff6d0cb5-thumbnail.jpg')

        context = super(SearchResult, self).get_context_data(**kwargs)

        context["tag_id"] = kwargs["tag_id"]

        photo_result_list = []
        for photo in Photo.objects.filter(tags__id=kwargs["tag_id"]):
            if photo.thumbnail is None:
                continue

            thumbnail_img = r.meta.client.generate_presigned_url('get_object',
                                                                Params={'Bucket': 'thumbnails',
                                                                        'Key': photo.thumbnail.object_storage_key,
                                                                        'ResponseContentType': 'image/jpeg'})

            photo_result = {}

            photo_result['thumbnail'] = thumbnail_img
            photo_result['url'] = photo.object_storage_key

            photo_result_list.append(photo_result)

        context["photos"] = photo_result_list

        return context
