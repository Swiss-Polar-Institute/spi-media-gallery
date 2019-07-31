import boto3
from django.conf import settings
import os
from main.utils import content_type_for_filename
import urllib


class SpiS3Utils(object):
    def __init__(self, bucket_name):
        if bucket_name not in settings.BUCKETS_CONFIGURATION:
            raise ValueError("Bucket name {} not found. Possible bucket names: {}".format(bucket_name, ", ".join(settings.BUCKETS_CONFIGURATION.keys())))

        self._bucket_configuration = settings.BUCKETS_CONFIGURATION[bucket_name]

    def resource(self):
        return boto3.resource(service_name="s3",
                              aws_access_key_id=self._bucket_configuration['access_key'],
                              aws_secret_access_key=self._bucket_configuration['secret_key'],
                              endpoint_url=self._bucket_configuration['endpoint'])

    def bucket(self):
        return self.resource().Bucket(self._bucket_configuration['name'])

    def objects_in_bucket(self, prefix=""):
        return self.bucket().objects.filter(Prefix=prefix).all()

    def get_set_of_keys(self, prefix=""):
        keys = set()

        for o in self.objects_in_bucket(prefix):
            keys.add(o.key)

        return keys

    def get_object(self, key):
        return self.resource().Object(self._bucket_configuration["name"], key)

    def upload_file(self, file_path, key):
        self.bucket().upload_file(file_path, key)

    def download_file(self, key, file_path):
        self.bucket().download_file(key, file_path)

    def get_presigned_link(self, key, response_content_type, response_content_disposition, filename):
        params = {'Bucket': self._bucket_configuration["name"],
                            'Key': key,
                            'ResponseContentType': response_content_type}

        if filename is not None:
            params['ResponseContentDisposition'] = "{}; filename={}".format(response_content_disposition, filename)

        return self.resource().meta.client.generate_presigned_url('get_object',
                                                             Params=params)

    def get_presigned_download_link(self, key, filename=None):
        if filename is None:
            filename = os.path.basename(key)

        return self.resource().meta.client.generate_presigned_url('get_object',
                                                             Params={'Bucket': self._bucket_configuration["name"],
                                                                     'Key': key,
                                                                     'ResponseContentDisposition': 'attachment; filename={}'.format(filename),
                                                                     'ResponseContentType' : 'application/image'})

    def list_files(self, prefix, only_from_extensions=None):
        files_set = set()
        files = self.bucket().objects.filter(Prefix=prefix).all()

        for file in files:
            if only_from_extensions is not None:
                basename, extension = os.path.splitext(file.key)

                if len(extension) > 0:
                    extension = extension[1:]

                extension = extension.lower()

                if extension not in only_from_extensions:
                    continue

            files_set.add(file.key.lstrip("/"))

        return files_set

def link_for_medium(medium, content_disposition, filename):
    content_type = content_type_for_filename(filename)
    # if medium_for_content_type.medium_type == Medium.PHOTO:
    #     content_type = "image/jpeg"
    # elif medium_for_content_type.medium_type == Medium.VIDEO:
    #     content_type = "video/webm"

    if settings.PROXY_TO_OBJECT_STORAGE:
        d = {"content_type": content_type,
             "content_disposition_type": content_disposition,
             "filename": filename,
             "bucket": medium.bucket_name()
        }

        return "/get/file/{}?{}".format(medium.md5, urllib.parse.urlencode(d))
    else:
        bucket = SpiS3Utils(medium.bucket_name())

        return bucket.get_presigned_link(medium.object_storage_key, content_type, content_disposition, filename)
