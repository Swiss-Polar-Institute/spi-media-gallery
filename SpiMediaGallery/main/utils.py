import hashlib
import os
import sys
import subprocess
import tempfile
from django.conf import settings

def image_size_label_abbreviation_to_presentation(abbreviation):
    from main.models import MediumResized

    for size in MediumResized.SIZES_OF_PHOTOS:
        if size[0] == abbreviation:
            return size[1]

    assert False


def hash_of_s3_object(s3_object):
    hash_md5 = hashlib.md5()
    for chunk in s3_object.get()["Body"].iter_chunks(100 * 1024 * 1024):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def hash_of_file_path(file_path):
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as fp:
        for chunk in iter(lambda: fp.read(100 * 1024 * 1024), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def resize_photo(input_file_path, width):
    output_file_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    output_file_path.close()

    with open(os.devnull, 'w') as devnull:
        command = ["convert", "-auto-orient"]
        if width is not None:
            command += ["-resize", "{}x{}".format(width, width)]

        command += [input_file_path, output_file_path.name]

        try:
            subprocess.run(command, stdout=devnull, stderr=devnull)
        except OSError:
            print("Error in the command:", command)
            sys.exit(1)

    return output_file_path.name


def resize_video(input_file_path, width):
    output_file_path = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    output_file_path.close()

    with open(os.devnull, "w") as devnull:
        # ffmpeg -y -i C0004.MP4 -vcodec vp8 -crf 27 -preset veryfast -c:a libvorbis -s 320x480 resized-320.webm
        size = "{}:-1".format(width)

        command = ["ffmpeg", "-y", "-i", input_file_path,
                   "-threads", "0",
                   "-vcodec", "vp8", "-crf", "27", "-preset", "veryfast", "-c:a", "libvorbis",
                   "-vf", "scale={}".format(size),
                   "-auto-alt-ref", "0",    # Fixes error: "Transparency encoding with auto_alt_ref does not work", "Error initializing output stream 0:0 -- Error while opening encoder for output stream #0:0 - maybe incorrect parameters such as bit_rate, rate, width or height"
                   "-max_muxing_queue_size", "4096", # Fixes error: "Too many packets buffered for output stream 0:1."
                   output_file_path.name]

        try:
            subprocess.run(command, stdout=devnull, stderr=devnull)
        except OSError:
            print("Error in the command:", command)
            sys.exit(1)

    output_file_path_name = output_file_path.name

    if os.stat(output_file_path_name).st_size == 0:
        # Encoding failed
        os.remove(output_file_path_name)
        return None

    return output_file_path_name


def bytes_to_human_readable(num):
    if num is None:
        return "Unknown"

    for unit in ['','KB','MB','GB','TB','PB','EB','ZB']:
        if abs(num) < 1024.0:
            return "{:.2f} {}".format(num, unit)
        num /= 1024.0
    return "%d %s" % (num, 'YB')


def seconds_to_minutes_seconds(seconds):
    if seconds is None:
        return "Unknown"

    return " {} min {} sec".format(seconds // 60, seconds % 60)


def seconds_to_human_readable(seconds):
    if seconds is None:
        return "Unknown"

    minutes = seconds / 60

    if minutes < 1:
        return "{:.2f} secs".format(seconds)

    hours = minutes / 60
    if hours < 1:
        return "{:.2f} mins".format(minutes)

    days = hours / 24
    if days < 1:
        return "{:.2f} hours".format(hours)

    return "{:.2f} days".format(days)


def content_type_for_filename(filename):
    extension = os.path.splitext(filename)[1][1:].lower()

    assert extension in (settings.PHOTO_EXTENSIONS | settings.VIDEO_EXTENSIONS)

    # Can add more from:
    # Raw images: https://stackoverflow.com/questions/43473056/which-mime-type-should-be-used-for-a-raw-image
    # Videos (and anything): https://www.sitepoint.com/mime-types-complete-list/

    extension_to_content_type = {'jpg': 'image/jpeg',
                                 'jpeg': 'image/jpeg',
                                 'cr2': 'image/x-canon-cr2',
                                 'arw': 'image/x-sony-arw',
                                 'nef': 'image/x-nikon-nef',
                                 'mp4': 'video/mp4',
                                 'mpeg': 'video/mpeg',
                                 'mov': 'video/quicktime',
                                 'avi': 'video/avi',
                                 'webm': 'video/webm'}

    assert extension in extension_to_content_type

    return extension_to_content_type[extension]


def filename_for_resized_medium(medium_id, photo_resize_label, extension):
    return "SPI-{}-{}.{}".format(medium_id, photo_resize_label, extension)


def filename_for_original_medium(medium):
    _, extension = os.path.splitext(medium.file.object_storage_key)

    extension = extension[1:]

    return "SPI-{}.{}".format(medium.pk, extension)


def human_readable_resolution_for_medium(medium):
    if medium.width is None or medium.height is None:
        return "Unknown resolution"
    else:
        return "{}x{}".format(medium.width, medium.height)


def file_extension(file_name):
    _, extension = os.path.splitext(file_name)

    if len(extension) > 0:
        extension = extension[1:]

    return extension


def convert_raw_to_ppm(file_name):
    # dcraw might generate a non .ppm but a .pgm?
    output_file = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)

    p = subprocess.Popen(["dcraw", "-c", file_name], stdout=output_file)
    p.wait()
    output_file.close()

    return output_file.name
