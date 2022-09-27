from django.urls import path, re_path
from django.views.decorators.cache import cache_page

from main.views import (  # isort:skip
    Display,
    DisplayRandom,
    GetFile,
    Homepage,
    ImportFromProjectApplicationCallback,
    ListVideos,
    ListVideosExportCsv,
    Map,
    PhotosGeojson,
    Search,
    SearchByMultipleTags,
    Stats,
    TrackGeojson,
    MediumUploadView,
)

urlpatterns = [
    path("", cache_page(60 * 15)(Homepage.as_view()), name="homepage"),
    path(
        "search/multiple_tags/",
        cache_page(60 * 15)(SearchByMultipleTags.as_view()),
        name="search_by_multiple_tags",
    ),
    re_path(
        "media/random/(?P<type_of_medium>photo|video|medium)/",
        DisplayRandom.as_view(),
        name="display_random",
    ),
    path("media/<int:media_id>", Display.as_view(), name="medium"),
    re_path("media/", Search.as_view(), name="search"),
    path("videos/list/", ListVideos.as_view(), name="list_videos"),
    path(
        "videos/list/export/csv/",
        ListVideosExportCsv.as_view(),
        name="list_videos_export_csv",
    ),
    path("stats/", Stats.as_view(), name="stats"),
    path("map/photos.geojson", PhotosGeojson.as_view()),
    path("map/", Map.as_view()),
    path("map/track.geojson", TrackGeojson.as_view()),
    path("get/file/<str:bucket_name>/<str:md5>", GetFile.as_view(), name="get_file"),
    path(
        "api/project_application/callback/import",
        ImportFromProjectApplicationCallback.as_view(),
        name="project-application-import-callback",
    ),
    path("api/v1/medium/", MediumUploadView.as_view(), name="upload_file"),
]
