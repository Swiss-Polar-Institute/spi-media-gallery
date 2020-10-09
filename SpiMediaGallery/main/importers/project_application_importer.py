from django.core.cache import cache

from .project_application_api_client import ProjectApplicationApiClient
from ..management.commands.generate_virtual_tags import GenerateTags
from ..management.commands.resize_media import Resizer


def import_resize_update_tags_from_project_application():
    # Creates the new Medium objects
    media_importer = ProjectApplicationApiClient()
    media_importer.import_new_media()

    # Resizes the photos
    bucket_name_resized = 'processed'
    sizes_type = ['T', 'S', 'L']
    media_type = 'Photos'
    resizer = Resizer(bucket_name_resized, sizes_type, media_type)
    resizer.resize_media()

    # Resizes the videos
    sizes_type = ['S', 'L']
    media_type = 'Videos'
    resizer = Resizer(bucket_name_resized, sizes_type, media_type)
    resizer.resize_media()

    # Re-generate tags
    generator = GenerateTags()
    generator.delete_generated_tags()
    generator.generate_tags()

    # Clears the cache: so the homepage tags are updated
    cache.clear()
