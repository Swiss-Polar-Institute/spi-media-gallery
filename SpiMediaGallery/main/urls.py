from django.urls import path, re_path
from main.views import Homepage, SearchMultipleTags, SearchMediumId, SearchBox, SearchNear, ListVideos, \
    SearchVideosExportCsv, Display, Map, PhotosGeojson, TrackGeojson, GetFile, \
    DisplayRandom

urlpatterns = [
    path('', Homepage.as_view()),
    re_path('display/random/(?P<type_of_medium>photo|video|medium)/', DisplayRandom.as_view(), name="display_random"),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('search/id/', SearchMediumId.as_view()),
    path('search/box/', SearchBox.as_view()),
    path('search/near', SearchNear.as_view()),
    path('list/videos/', ListVideos.as_view()),
    path('list/videos/export/csv/', SearchVideosExportCsv.as_view()),
    path('display/<int:media_id>', Display.as_view(), name="medium"),
    path('map/photos.geojson', PhotosGeojson.as_view()),
    path('map/', Map.as_view()),
    path('map/track.geojson', TrackGeojson.as_view()),
    path('get/file/<str:md5>', GetFile.as_view())
]
