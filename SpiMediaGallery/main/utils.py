import hashlib
import os
import subprocess


def hash_of_s3_object(s3_object):
    hash_md5 = hashlib.md5()
    for chunk in s3_object.get()["Body"].iter_chunks(100 * 1024 * 1024):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def hash_of_fp(file_path):
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as fp:
        for chunk in iter(lambda: fp.read(100 * 1024 * 1024), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def resize_file(input_file_path, output_file_path, width):
    with open(os.devnull, 'w') as devnull:
        subprocess.run(["convert", "-resize", "{}x{}".format(width, width), input_file_path, output_file_path], stdout=devnull,
                                                                                         stderr=devnull)
