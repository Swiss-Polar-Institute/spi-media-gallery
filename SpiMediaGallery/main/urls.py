from django.urls import path
from main.views import Homepage, SearchMultipleTags, SearchMediumId, SearchBox, SearchNear, ListVideos, \
    SearchVideosExportCsv, Display, RandomPhoto, RandomVideo, RandomMedium, Map, PhotosGeojson, TrackGeojson, GetFile, \
    Search

urlpatterns = [
    path('', Homepage.as_view()),
    path('search/', Search.as_view()),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('search/id/', SearchMediumId.as_view()),
    path('search/box/', SearchBox.as_view()),
    path('search/near', SearchNear.as_view()),
    path('list/videos/', ListVideos.as_view()),
    path('list/videos/export/csv/', SearchVideosExportCsv.as_view()),
    path('display/<int:media_id>', Display.as_view(), name="medium"),
    path('display/random/photo/', RandomPhoto.as_view()),
    path('display/random/video/', RandomVideo.as_view()),
    path('display/random/medium/', RandomMedium.as_view()),
    path('map/photos.geojson', PhotosGeojson.as_view()),
    path('map/', Map.as_view()),
    path('map/track.geojson', TrackGeojson.as_view()),
    path('get/file/<str:md5>', GetFile.as_view())
]
