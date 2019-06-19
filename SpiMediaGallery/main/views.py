from django.shortcuts import render

from django.http import HttpResponse
from django.views.generic import TemplateView
from main.models import Photo, PhotoResized, Tag

import boto3

from main.spi_s3_utils import SpiS3Utils


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
        r = boto3.resource(service_name="s3",
                       aws_access_key_id="minio",
                       aws_secret_access_key="minio123",
                       endpoint_url="http://localhost:9000")

        context = super(Search, self).get_context_data(**kwargs)

        query_photos_for_tag = Photo.objects.filter(tags__id=kwargs["tag_id"])

        context["tag_name"] = Tag.objects.get(id=kwargs["tag_id"])
        context["total_number_photos_tag"] = len(query_photos_for_tag)

        photo_result_list = []
        for photo in query_photos_for_tag:
            thumbnail = PhotoResized.objects.filter(photo=photo).filter(size_label="T")

            if len(thumbnail) == 1:
                thumbnail_key = thumbnail[0].object_storage_key
                thumbnail_img = r.meta.client.generate_presigned_url('get_object',
                                                                    Params={'Bucket': 'thumbnails',
                                                                            'Key': thumbnail_key,
                                                                            'ResponseContentType': 'image/jpeg'})

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


class Display(TemplateView):
    template_name = "display.tmpl"

    def get_context_data(self, **kwargs):
        context = super(Display, self).get_context_data(**kwargs)

        spi_s3_utils = SpiS3Utils("thumbnails")

        photo_resized = PhotoResized.objects.filter(photo__id=kwargs['photo_id']).filter(size_label="S")[0]
        photo = Photo.objects.get(id=kwargs['photo_id'])

        context['photo_small_url'] = spi_s3_utils.get_presigned_jpeg_link(photo_resized.object_storage_key)
        context['media_file'] = photo.object_storage_key


        context['list_of_tags'] = photo.tags.all()

        return context
