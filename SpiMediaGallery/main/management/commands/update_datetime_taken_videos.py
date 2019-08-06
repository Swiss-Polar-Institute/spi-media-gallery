# This can be incorporated (missing the duration at the moment9 into update_datetime_taken

from django.core.management.base import BaseCommand, CommandError

from main.models import Medium
from django.conf import settings
import sys
from django.utils import timezone

import datetime
import tempfile
import os
from pymediainfo import MediaInfo
from django.db.models import Sum

from main import spi_s3_utils
from main.progress_report import ProgressReport

import time
from main import utils


class Command(BaseCommand):
    help = 'Updates date time taken'

    def add_arguments(self, parser):
        parser.add_argument('bucket_name_media', type=str, help="Bucket name - it needs to exist in settings.py in BUCKETS_CONFIGURATION")

    def handle(self, *args, **options):
        bucket_name_media = options["bucket_name_media"]

        updater = UpdateDateTimeTaken(bucket_name_media)

        updater.update_media()


def get_information_from_video(video_file):
    information = {}

    video_information = MediaInfo.parse(video_file)

    for track in video_information.tracks:
        if track.track_type == "Video":
            information['width'] = track.width
            information['height'] = track.height
            information['duration'] = float(track.duration) / 1000
            if track.encoded_date is not None:
                dt = datetime.datetime.strptime(track.encoded_date, "UTC %Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                information['date_encoded'] = dt

            else:
                information['date_encoded'] = None

    return information


class UpdateDateTimeTaken(object):
    def __init__(self, bucket_name_media):
        self._media_bucket = spi_s3_utils.SpiS3Utils(bucket_name_media)

    @staticmethod
    def _update_information_from_video(video, video_file):
        if video.width is None or video.height is None or video.duration is None or video.datetime_taken is None:
            information = get_information_from_video(video_file)

            video.width = information['width']
            video.height = information['height']
            video.duration = information['duration']
            video.datetime_taken = information['date_encoded']

            video.save()

    def update_media(self):
        videos_to_update = Medium.objects.filter(datetime_taken__isnull=True).filter(width__isnull=False).filter(medium_type=Medium.VIDEO)

        if len(videos_to_update) == 0:
            print("Nothing to be updated? Aborting")
            sys.exit(1)

        total_bytes = videos_to_update.aggregate(Sum('file__size'))['file__size__sum']

        progress_report = ProgressReport(total_bytes,
                                         extra_information="Updating medium",
                                         steps_are_bytes=True)

        for video in videos_to_update:
            # Download Media file from the bucket
            media_file = tempfile.NamedTemporaryFile(delete=False)
            media_file.close()
            start_download = time.time()
            self._media_bucket.bucket().download_file(video.object_storage_key, media_file.name)
            download_time = time.time() - start_download

            assert os.stat(media_file.name).st_size == video.file.size

            download_speed = (video.file.size / 1024 / 1024) / download_time        # MB/s
            print("Download Stats: Total size: {} Time: {} Speed: {:.2f} MB/s File: {}".format(utils.bytes_to_human_readable(video.file.size),
                                                                                      utils.seconds_to_human_readable(download_time),
                                                                                      download_speed,
                                                                                      video.object_storage_key))

            self._update_information_from_video(video, media_file.name)

            os.remove(media_file.name)

            progress_report.increment_steps_and_print_if_needed(video.file.size)