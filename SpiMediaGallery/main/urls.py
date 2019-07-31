from django.urls import path, re_path
from main.views import Homepage, ListVideos, \
    ListVideosExportCsv, Display, Map, PhotosGeojson, TrackGeojson, GetFile, \
    DisplayRandom, Search

urlpatterns = [
    path('', Homepage.as_view()),
    re_path('display/random/(?P<type_of_medium>photo|video|medium)/', DisplayRandom.as_view(), name="display_random"),
    re_path('search/', Search.as_view(), name="search"),
    path('list/videos/', ListVideos.as_view(), name="list_videos"),
    path('list/videos/export/csv/', ListVideosExportCsv.as_view(), name="list_videos_export_csv"),
    path('display/<int:media_id>', Display.as_view(), name="medium"),
    path('map/photos.geojson', PhotosGeojson.as_view()),
    path('map/', Map.as_view()),
    path('map/track.geojson', TrackGeojson.as_view()),
    path('get/file/<str:md5>', GetFile.as_view(), name="get_file")
]
