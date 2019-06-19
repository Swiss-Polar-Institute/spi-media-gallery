import boto3
from django.conf import settings


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
        self.bucket().meta.client.upload_file(file_path, self._bucket_configuration["name"], key)

    def get_presigned_jpeg_link(self, key):
        return self.resource().meta.client.generate_presigned_url('get_object',
                                                             Params={'Bucket': self._bucket_configuration["name"],
                                                                     'Key': key,
                                                                     'ResponseContentType': 'image/jpeg'})