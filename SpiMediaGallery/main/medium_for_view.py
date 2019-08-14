from main.models import Medium, MediumResized
import math
from django.contrib.staticfiles.templatetags.staticfiles import static
from main import utils
from main.utils import filename_for_resized_medium, filename_for_medium, human_readable_resolution_for_medium, \
    link_for_medium
from django.db import models

from typing import List, Dict, Any, Optional


class MediumForViewManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related('mediumresized_set').prefetch_related('mediumresized_set__file').select_related('file')


class MediumForView(Medium):
    URL_SMALL_DO_NOT_EXIST = static("images/small-does-not-exist.jpg")
    URL_THUMBNAIL_DO_NOT_EXIST = static("images/thumbnail-does-not-exist.jpg")

    objects = MediumForViewManager()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _thumbnail_size(self) -> Optional[str]:
        if self.medium_type == Medium.PHOTO:
            return MediumResized.THUMBNAIL
        elif self.medium_type == Medium.VIDEO:
            return MediumResized.SMALL

        assert False

    def thumbnail_url(self) -> str:
        size_label = self._thumbnail_size()
        medium_resized = self._medium_resized(size_label)

        if medium_resized is None:
            return self.URL_THUMBNAIL_DO_NOT_EXIST

        resized_extension = utils.file_extension(medium_resized.file.object_storage_key)

        return link_for_medium(medium_resized.file, "inline",
                               filename_for_resized_medium(self.pk, size_label, resized_extension))

    def original_file_attachment_url(self) -> str:
        return link_for_medium(self.file, "attachment", filename_for_medium(self))

    def small_resolution_url(self) -> str:
        return self._url(MediumResized.SMALL)

    def large_resolution_url(self) -> str:
        return self._url(MediumResized.LARGE)

    def _url(self, size_label: str) -> str:
        resized = self._medium_resized(size_label)

        if resized is None:
            return self.URL_SMALL_DO_NOT_EXIST

        return link_for_medium(resized.file, "inline",
                               filename_for_resized_medium(self.pk, size_label, utils.file_extension(resized.file.object_storage_key)))

    def file_size_original(self) -> str:
        return utils.bytes_to_human_readable(self.file.size)

    def _file_size(self, size_label) -> Optional[str]:
        resized = self._medium_resized(size_label)

        if resized is None:
            return None

        return utils.bytes_to_human_readable(resized.file.size)

    def file_size_small(self) -> Optional[str]:
        return self._file_size(MediumResized.SMALL)

    def file_size_large(self) -> Optional[str]:
        return self._file_size(MediumResized.LARGE)

    def is_small_resolution_available(self) -> bool:
        resized = self._medium_resized(MediumResized.SMALL)

        return resized is not None

    def is_large_resolution_available(self) -> bool:
        resized = self._medium_resized(MediumResized.LARGE)

        return resized is not None

    def duration_in_minutes_seconds(self) -> str:
        return utils.seconds_to_minutes_seconds(self.duration)

    def video_embed_responsive_ratio(self) -> str:
        if self.width is not None and self.height is not None and math.isclose(self.width / self.height, 16/9):
            return "embed-responsive-16by9"

        return "embed-responsive-16by9"

    def thumbnail_content_type(self) -> str:
        size_label = self._thumbnail_size()

        thumbnail = self._medium_resized(size_label)

        if thumbnail is None:
            # For some files the thumbnail could not be done or is not already done
            return utils.content_type_for_filename(self.URL_THUMBNAIL_DO_NOT_EXIST)

        return utils.content_type_for_filename(thumbnail.file.object_storage_key)

    def border_color(self) -> str:
        if self.medium_type == Medium.VIDEO:
            return "border-dark"

    def resolution_for_original(self) -> str:
        if self.width is None or self.height is None:
            return "Unknown"

        return "{}x{}".format(self.width, self.height)

    def file_name(self) -> str:
        return "SPI-{}.{}".format(self.pk, utils.file_extension(self.file.object_storage_key))

    def list_of_tags(self) -> List[Dict[str, Any]]:
        list_of_tags = []

        for tag in self.tags.all():
            t = {'id': tag.id, 'tag': tag.name.name}
            list_of_tags.append(t)

        list_of_tags = sorted(list_of_tags, key=lambda k: k['tag'])

        return list_of_tags

    def list_of_resized(self) -> List[Dict[str, Any]]:
        medium_resized_all = self.mediumresized_set.all()

        sizes_presentation = []

        for medium_resized in medium_resized_all:
            if medium_resized.size_label == MediumResized.THUMBNAIL:
                continue

            size_information = {}

            size_information['label'] = utils.image_size_label_abbreviation_to_presentation(medium_resized.size_label)
            size_information['size'] = utils.bytes_to_human_readable(medium_resized.file.size)
            size_information['width'] = medium_resized.width

            size_information['resolution'] = human_readable_resolution_for_medium(medium_resized)

            filename = filename_for_resized_medium(self.pk, medium_resized.size_label, utils.file_extension(medium_resized.file.object_storage_key))

            size_information['image_link'] = link_for_medium(medium_resized.file, "inline", filename)

            sizes_presentation.append(size_information)

        return sorted(sizes_presentation, key=lambda k: k['width'])

    def copyright_text(self) -> str:
        if self.copyright is None:
            return "Unknown"
        else:
            return self.copyright.public_text

    def license_text(self) -> str:
        if self.license is None:
            return "Unknown"
        else:
            return self.license.public_text

    def photographer_name(self) -> str:
        if self.photographer is None:
            return "Unknown"
        else:
            return "{} {}".format(self.photographer.first_name, self.photographer.last_name)

    def is_photo(self) -> bool:
        return self.medium_type == self.PHOTO

    def is_video(self) -> bool:
        return self.medium_type == self.VIDEO

    def _medium_resized(self, label):
        for mediumresized in self.mediumresized_set.all():
            if mediumresized.size_label == label:
                return mediumresized
        return None

    class Meta:
        proxy = True

