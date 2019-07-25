import hashlib
import os
import sys
import subprocess
import tempfile

from main.models import MediumResized


def image_size_label_abbreviation_to_presentation(abbreviation):
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
                   output_file_path.name]

        try:
            subprocess.run(command, stdout=devnull, stderr=devnull)
        except OSError:
            print("Error in the command:", command)
            sys.exit(1)

    return output_file_path.name


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
