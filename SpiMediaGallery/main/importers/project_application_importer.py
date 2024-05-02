from django.core.cache import cache

from ..management.commands.generate_virtual_tags import GenerateTags
from ..management.commands.resize_media import Resizer
from .project_application_api_client import ProjectApplicationApiClient


def import_resize_update_tags_from_project_application():
    # Creates the new Medium objects
    media_importer = ProjectApplicationApiClient()

    tags_deleted_media = media_importer.delete_deleted_media()

    # Resizes the photos
    bucket_name_resized = "processed"
    sizes_type = ["T", "S", "M", "L", "O"]
    media_type = "Photos"
    resizer = Resizer(bucket_name_resized, sizes_type, media_type)
    resizer.resize_media()

    # Resizes the videos
    sizes_type = ["T", "S", "L"]
    media_type = "Videos"
    resizer = Resizer(bucket_name_resized, sizes_type, media_type)
    resizer.resize_media()

    # Tags cleanup
    generator = GenerateTags()
    generator.delete_tags_if_orphaned(tags_deleted_media)

    # Clears the cache: so the homepage tags are updated
    cache.clear()
