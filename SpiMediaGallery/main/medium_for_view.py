from main.models import Medium, MediumResized
import math
import os
from django.contrib.staticfiles.templatetags.staticfiles import static
from main import utils
from main.spi_s3_utils import SpiS3Utils, link_for_medium
from main.utils import filename_for_resized_medium, filename_for_original_medium, human_readable_resolution_for_medium

class MediumForView(Medium):
    def _medium_resized(self, label):
        qs = MediumResized.objects.filter(medium=self).filter(size_label=label)
        assert len(qs) < 2

        if len(qs) == 1:
            return qs[0]
        else:
            return None

    def link_for_thumbnail_resolution(self):
        if self.medium_type == Medium.PHOTO:
            medium_resized = self._medium_resized("T")

            if medium_resized is None:
                return static("images/thumbnail-does-not-exist.jpg")

            return link_for_medium(medium_resized, "inline", filename_for_resized_medium(self.pk, "T", "jpg"))

        elif self.medium_type == Medium.VIDEO:
            medium_resized = self._medium_resized("S")

            if medium_resized is None:
                return static("images/thumbnail-does-not-exist.jpg")

            return link_for_medium(medium_resized, "inline", filename_for_resized_medium(self.pk, "S", "webm"))

        else:
            assert False

    def link_for_original(self):
        return link_for_medium(self, "attachment", filename_for_original_medium(self))

    def file_size_for_original(self):
        return utils.bytes_to_human_readable(self.file_size)

    def link_for_small_resolution(self):
        resized = self._medium_resized("S")
        if resized is None:
            return static("images/small-does-not-exist.jpg")

        return link_for_medium(resized, "inline", filename_for_resized_medium(self.pk, "S", resized.file_extension()))

    def small_resolution_exist(self):
        resized = self._medium_resized("S")

        return resized is not None

    def file_size_for_small_resolution(self):
        resized = self._medium_resized("S")

        if resized is None:
            return None

        return utils.bytes_to_human_readable(resized.file_size)

    def duration_in_minutes_seconds(self):
        return utils.seconds_to_minutes_seconds(self.duration)

    def video_embed_responsive_ratio(self):
        if self.width is not None and self.height is not None and math.isclose(self.width / self.height, 16/9):
            return "embed-responsive-16by9"

        return "embed-responsive-16by9"

    def small_content_type(self):
        if self.medium_type == Medium.VIDEO:
            return "video/webm"
        else:
            return "image/jpeg"

    def border_color(self):
        if self.medium_type == Medium.VIDEO:
            return "border-dark"

    def resolution_for_original(self):
        if self.width is None or self.height is None:
            return "Unknown"

        return "{}x{}".format(self.width, self.height)

    def file_extension(self):
        _ , file_extension = os.path.splitext(self.object_storage_key)

        if file_extension is None:
            return "unknown"

        if len(file_extension) == 0:
            return ""

        file_extension = file_extension[1:]

        return file_extension

    def file_id(self):
        return "SPI-{}.{}".format(self.pk, self.file_extension())

    def copyright_render(self):
        if self.copyright is None:
            return "Unknown"
        else:
            return self.copyright.public_text

    def license_render(self):
        if self.license is None:
            return "Unknown"
        else:
            return self.license.public_text

    def photographer_render(self):
        if self.photographer is None:
            return "Unknown"
        else:
            return "{} {}".format(self.photographer.first_name, self.photographer.last_name)

    def list_of_tags(self):
        list_of_tags = []

        for tag in self.tags.all():
            t = {'id': tag.id, 'tag': tag.tag}
            list_of_tags.append(t)

        list_of_tags = sorted(list_of_tags, key=lambda k: k['tag'])

        return list_of_tags

    def resizeds(self):
        medium_resized_all = MediumResized.objects.filter(medium=self)

        sizes_presentation = []

        for medium_resized in medium_resized_all:
            if medium_resized.size_label == "T":
                continue

            size_information = {}

            size_information['label'] = utils.image_size_label_abbreviation_to_presentation(medium_resized.size_label)
            size_information['size'] = utils.bytes_to_human_readable(medium_resized.file_size)
            size_information['width'] = medium_resized.width

            size_information['resolution'] = human_readable_resolution_for_medium(medium_resized)

            filename = filename_for_resized_medium(self.pk, medium_resized.size_label, medium_resized.file_extension())

            size_information['image_link'] = link_for_medium(medium_resized, "inline", filename)

            sizes_presentation.append(size_information)

        return sorted(sizes_presentation, key=lambda k: k['width'])

    def is_photo(self):
        return self.medium_type == self.PHOTO

    def is_video(self):
        return self.medium_type == self.VIDEO

    class Meta:
        proxy = True

