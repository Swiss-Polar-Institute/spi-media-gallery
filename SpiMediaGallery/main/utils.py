import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib
from typing import Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone

from .models import File, Medium, TagName, Tag
from .spi_s3_utils import SpiS3Utils


def image_size_label_abbreviation_to_presentation(abbreviation: str) -> Optional[str]:
    from main.models import MediumResized

    for size in MediumResized.SIZES_OF_MEDIA:
        if size[0] == abbreviation:
            return size[1]

    assert False


def hash_of_s3_object(s3_object) -> str:
    hash_md5 = hashlib.md5()
    for chunk in s3_object.get()['Body'].iter_chunks(100 * 1024 * 1024):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def hash_of_file_path(file_path: str) -> str:
    hash_md5 = hashlib.md5()

    with open(file_path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(100 * 1024 * 1024), b''):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def resize_photo(input_file_path: int, width: int) -> Optional[str]:
    output_file_path = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    output_file_path.close()
    output_file_path_name = output_file_path.name

    with open(os.devnull, 'w') as devnull:
        command = ['convert', '-auto-orient']
        if width is not None:
            command += ['-resize', '{}x{}'.format(width, width)]

        command += [input_file_path, output_file_path_name]

        try:
            subprocess.run(command, stdout=devnull, stderr=devnull)
        except OSError:
            os.remove(output_file_path_name)

            print('Error in the command:', command)
            sys.exit(1)

        if os.stat(output_file_path_name).st_size == 0:
            os.remove(output_file_path_name)
            return None

    return output_file_path_name


def resize_video(input_file_path: str, width: int) -> Optional[str]:
    output_file_path = tempfile.NamedTemporaryFile(suffix='.webm', delete=False)
    output_file_path.close()
    output_file_path_name = output_file_path.name

    with open(os.devnull, 'w') as devnull:
        # ffmpeg -y -i C0004.MP4 -vcodec vp8 -crf 27 -preset veryfast -c:a libvorbis -s 320x480 resized-320.webm
        size = '{}:-1'.format(width)

        command = ['ffmpeg', '-y', '-i', input_file_path,
                   '-threads', '0',
                   '-vcodec', 'vp8', '-crf', '27', '-preset', 'veryfast', '-c:a', 'libvorbis',
                   '-vf', 'scale={}'.format(size),
                   '-auto-alt-ref', '0',
                   # Fixes error: 'Transparency encoding with auto_alt_ref does not work', 'Error initializing output stream 0:0 -- Error while opening encoder for output stream #0:0 - maybe incorrect parameters such as bit_rate, rate, width or height'
                   '-max_muxing_queue_size', '4096',  # Fixes error: 'Too many packets buffered for output stream 0:1.'
                   output_file_path_name]

        try:
            subprocess.run(command, stdout=devnull, stderr=devnull)
        except OSError:
            print('Error in the command:', command)
            sys.exit(1)

    if os.stat(output_file_path_name).st_size == 0:
        # Encoding failed
        os.remove(output_file_path_name)
        return None

    return output_file_path_name


def bytes_to_human_readable(num: int) -> str:
    if num is None:
        return 'Unknown'

    for unit in ['', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
        if abs(num) < 1024.0:
            return '{:.2f} {}'.format(num, unit)
        num /= 1024.0
    return '%d %s' % (num, 'YB')


def seconds_to_minutes_seconds(seconds: float) -> str:
    if seconds is None:
        return 'Unknown'

    return ' {} min {} sec'.format(seconds // 60, seconds % 60)


def seconds_to_human_readable(seconds: float) -> str:
    if seconds is None:
        return 'Unknown'

    minutes = seconds / 60

    if minutes < 1:
        return '{:.2f} secs'.format(seconds)

    hours = minutes / 60
    if hours < 1:
        return '{:.2f} mins'.format(minutes)

    days = hours / 24
    if days < 1:
        return '{:.2f} hours'.format(hours)

    return '{:.2f} days'.format(days)


def content_type_for_filename(filename: str) -> str:
    extension: str = os.path.splitext(filename)[1][1:].lower()

    assert extension in (settings.PHOTO_FORMATS.keys() | settings.VIDEO_FORMATS.keys())

    if extension in settings.PHOTO_FORMATS:
        return settings.PHOTO_FORMATS[extension].content_type
    elif extension in settings.VIDEO_FORMATS:
        return settings.VIDEO_FORMATS[extension].content_type
    else:
        assert False


def filename_for_resized_medium(medium_id: int, photo_resize_label: str, extension: str) -> str:
    return 'SPI-{}-{}.{}'.format(medium_id, photo_resize_label, extension)


def filename_for_medium(medium: Medium) -> str:
    _, extension = os.path.splitext(medium.file.object_storage_key)

    extension = extension[1:]

    return 'SPI-{}.{}'.format(medium.pk, extension)


def human_readable_resolution_for_medium(medium: Medium) -> str:
    if medium.width is None or medium.height is None:
        return 'Unknown resolution'
    else:
        return '{}x{}'.format(medium.width, medium.height)


def get_file_extension(file_name: str) -> str:
    _, extension = os.path.splitext(file_name)

    if len(extension) > 0:
        extension = extension[1:]

    return extension


def convert_raw_to_ppm(file_name: str) -> str:
    # dcraw might generate a non .ppm but a .pgm?
    output_file = tempfile.NamedTemporaryFile(suffix='.ppm', delete=False)

    p = subprocess.Popen(['dcraw', '-c', file_name], stdout=output_file)
    p.wait()
    output_file.close()

    return output_file.name


def get_medium_information(image_filepath: str) -> Dict[str, str]:
    command: List[str] = ['exiftool', '-json', image_filepath]

    run = subprocess.run(command, stdout=subprocess.PIPE)
    output = run.stdout
    output = output.decode('utf-8')
    exif = json.loads(output)[0]

    image_information = {}
    image_information['width'] = exif.get('ImageWidth', None)
    image_information['height'] = exif.get('ImageHeight', None)

    date_field: Optional[datetime] = None

    if 'DateTimeOriginal' in exif:
        date_field = 'DateTimeOriginal'
    elif 'CreateDate' in exif:
        date_field = 'CreateDate'

    if date_field is not None and exif[date_field] != '0000:00:00 00:00:00':
        datetime_original = exif[date_field]

        possible_formats = ['%Y:%m:%d %H:%M:  ',
                            '%Y:%m:%d %H:%MZ',
                            '%Y:%m:%d %H:%M:%S%z',
                            '%Y:%m:%d %H:%M%z',
                            '%Y:%m:%d %H:%M:%S',
                            '%Y:%m:%d %H:%M:',
                            '%Y:%m:%d %H:%M']

        for possible_format in possible_formats:
            try:
                datetime_processed = datetime.datetime.strptime(datetime_original, possible_format)

                if datetime_processed.tzinfo is None:
                    datetime_processed = datetime_processed.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        else:
            raise ValueError('Cannot convert string to date: _{}_'.format(datetime_original))

        image_information['datetime_taken'] = datetime_processed

    return image_information


def link_for_medium(file: File, content_disposition: str, filename: str) -> str:
    content_type = content_type_for_filename(filename)

    if settings.PROXY_TO_OBJECT_STORAGE:
        d = {'content_type': content_type,
             'content_disposition_type': content_disposition,
             'filename': filename,
             }

        return '{}?{}'.format(reverse('get_file', args=[file.bucket, file.md5]), urllib.parse.urlencode(d))
    else:
        bucket = SpiS3Utils(file.bucket_name())

        return bucket.get_presigned_link(file.object_storage_key, content_type, content_disposition, filename)


def set_tags(medium, tags):
    # Delete existing tags of the Medium to import it again
    medium.tags.clear()

    for tag in tags:
        # Find or create the tag_name
        try:
            tag_name = TagName.objects.get(name=tag)
        except ObjectDoesNotExist:
            tag_name = TagName()
            tag_name.name = tag
            tag_name.save()

        # Find or create the tag_name tag with XMP
        try:
            tag = Tag.objects.get(name=tag_name, importer=Tag.XMP)
        except ObjectDoesNotExist:
            tag = Tag(name=tag_name, importer=Tag.XMP)
            tag.save()

        medium.tags.add(tag)


def get_type(extension):
    if extension in settings.PHOTO_FORMATS:
        return Medium.PHOTO
    elif extension in settings.VIDEO_FORMATS:
        return Medium.VIDEO
    else:
        assert False
