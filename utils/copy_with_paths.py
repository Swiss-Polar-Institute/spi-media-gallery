#!/usr/bin/env python3

import argparse
import os
import shutil
import errno
import pathlib
import sys

FILE_EXTENSION = "xmp"


def copy_files(source, destination):
    if os.path.exists(destination):
        sys.stderr.write("Destination exists ({}). Aborting, please use a destination that doesn't exist\n".format(destination))
        sys.exit(1)

    source_list = pathlib.Path(source).parts[1:]

    count = 0
    for root, dirs, files in os.walk(source):
        for file in files:
            extension = os.path.splitext(file)[1].lstrip(".").lower()

            if extension != FILE_EXTENSION:
                continue

            # On Windows it removes the drive (c:/)
            # On Linux/Mac it removes the initial (/)

            this_path_list = pathlib.Path(root).parts[1:]
            this_path_list = this_path_list[len(source_list):]

            destination_directory = os.path.join(destination, *this_path_list)

            destination_file = os.path.join(destination_directory, file)
            source_file = os.path.join(root, file)

            try:
                os.makedirs(destination_directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            shutil.copy(source_file, destination_file)
            count += 1
            print("Copied {} to {}".format(source_file, destination_file))

    print("Finished! Copied {} files to: {}".format(count, destination))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy XMP files with paths")
    parser.add_argument("source", help="Source directory")
    parser.add_argument("destination", help="Destination directory")

    args = parser.parse_args()

    copy_files(args.source, args.destination)
