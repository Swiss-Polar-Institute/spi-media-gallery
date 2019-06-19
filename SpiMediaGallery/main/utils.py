import hashlib
import os
import subprocess

from main.models import PhotoResized


def image_size_label_abbreviation_to_presentation(abbreviation):
    for size in PhotoResized.SIZES_OF_PHOTOS:
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


def resize_file(input_file_path, output_file_path, width):
    with open(os.devnull, 'w') as devnull:
        command = ["convert", "-auto-orient"]
        if width is not None:
            command += ["-resize", "{}x{}".foprmat(width, width)]

        command += [input_file_path, output_file_path]

        subprocess.run(command, stdout=devnull, stderr=devnull)