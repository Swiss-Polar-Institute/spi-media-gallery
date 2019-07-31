from main.models import Medium, MediumResized
import math
import os
from django.contrib.staticfiles.templatetags.staticfiles import static
from main import utils
from main.spi_s3_utils import link_for_medium
from main.utils import filename_for_resized_medium, filename_for_original_medium, human_readable_resolution_for_medium


class MediumForView(Medium):
    def thumbnail_url(self):
        if self.medium_type == Medium.PHOTO:
            size_label = "T"
        elif self.medium_type == Medium.VIDEO:
            size_label = "S"
        else:
            assert False

        medium_resized = self._medium_resized(size_label)

        if medium_resized is None:
            return static("images/thumbnail-does-not-exist.jpg")

        resized_extension = MediumForView._get_file_extension(medium_resized.object_storage_key)

        return link_for_medium(medium_resized, "inline",
                               filename_for_resized_medium(self.pk, size_label, resized_extension))

    def original_file_attachment_url(self):
        return link_for_medium(self, "attachment", filename_for_original_medium(self))

    def small_resolution_url(self):
        resized = self._medium_resized(MediumResized.SMALL)
        if resized is None:
            return static("images/small-does-not-exist.jpg")

        return link_for_medium(resized, "inline",
                               filename_for_resized_medium(self.pk, MediumResized.SMALL, resized.file_extension()))

    def file_size_original(self):
        return utils.bytes_to_human_readable(self.file_size)

    def file_size_small(self):
        resized = self._medium_resized(MediumResized.SMALL)

        if resized is None:
            return None

        return utils.bytes_to_human_readable(resized.file_size)

    def is_small_resolution_available(self):
        resized = self._medium_resized(MediumResized.SMALL)

        return resized is not None

    def duration_in_minutes_seconds(self):
        return utils.seconds_to_minutes_seconds(self.duration)

    def video_embed_responsive_ratio(self):
        if self.width is not None and self.height is not None and math.isclose(self.width / self.height, 16/9):
            return "embed-responsive-16by9"

        return "embed-responsive-16by9"

    def resized_content_type(self):
        if self.medium_type == Medium.VIDEO:
            return "video/webm"
        elif self.medium_type == Medium.PHOTO:
            return "image/jpeg"
        else:
            assert False

    def border_color(self):
        if self.medium_type == Medium.VIDEO:
            return "border-dark"

    def resolution_for_original(self):
        if self.width is None or self.height is None:
            return "Unknown"

        return "{}x{}".format(self.width, self.height)

    def file_name(self):
        return "SPI-{}.{}".format(self.pk, self._get_file_extension(self.object_storage_key))

    def list_of_tags(self):
        list_of_tags = []

        for tag in self.tags.all():
            t = {'id': tag.id, 'tag': tag.tag}
            list_of_tags.append(t)

        list_of_tags = sorted(list_of_tags, key=lambda k: k['tag'])

        return list_of_tags

    def list_of_resized(self):
        medium_resized_all = MediumResized.objects.filter(medium=self)

        sizes_presentation = []

        for medium_resized in medium_resized_all:
            if medium_resized.size_label == MediumResized.THUMBNAIL:
                continue

            size_information = {}

            size_information['label'] = utils.image_size_label_abbreviation_to_presentation(medium_resized.size_label)
            size_information['size'] = utils.bytes_to_human_readable(medium_resized.file_size)
            size_information['width'] = medium_resized.width

            size_information['resolution'] = human_readable_resolution_for_medium(medium_resized)

            filename = filename_for_resized_medium(self.pk, medium_resized.size_label, MediumForView._get_file_extension(medium_resized.object_storage_key))

            size_information['image_link'] = link_for_medium(medium_resized, "inline", filename)

            sizes_presentation.append(size_information)

        return sorted(sizes_presentation, key=lambda k: k['width'])

    def copyright_text(self):
        if self.copyright is None:
            return "Unknown"
        else:
            return self.copyright.public_text

    def license_text(self):
        if self.license is None:
            return "Unknown"
        else:
            return self.license.public_text

    def photographer_name(self):
        if self.photographer is None:
            return "Unknown"
        else:
            return "{} {}".format(self.photographer.first_name, self.photographer.last_name)

    def is_photo(self):
        return self.medium_type == self.PHOTO

    def is_video(self):
        return self.medium_type == self.VIDEO

    def _medium_resized(self, label):
        qs = MediumResized.objects.filter(medium=self).filter(size_label=label)
        assert len(qs) < 2

        if len(qs) == 1:
            return qs[0]
        else:
            return None

    @staticmethod
    def _get_file_extension(filename):
        _ , file_extension = os.path.splitext(filename)

        if file_extension is None:
            return "unknown"

        if len(file_extension) == 0:
            return ""

        file_extension = file_extension[1:]

        return file_extension

    class Meta:
        proxy = True

