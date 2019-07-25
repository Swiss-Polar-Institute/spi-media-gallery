from django.urls import path
from main.views import Homepage, SearchMultipleTags, SearchMediumId, SearchBox, SearchNear, SearchVideos, \
    Display, RandomPhoto, RandomVideo, Map, PhotosGeojson, TrackGeojson, GetPhoto

urlpatterns = [
    path('', Homepage.as_view()),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('search/id/', SearchMediumId.as_view()),
    path('search/box/', SearchBox.as_view()),
    path('search/near', SearchNear.as_view()),
    path('search/videos/', SearchVideos.as_view()),
    path('display/<int:media_id>', Display.as_view()),
    path('display/random/photo/', RandomPhoto.as_view()),
    path('display/random/video/', RandomVideo.as_view()),
    path('map/photos.geojson', PhotosGeojson.as_view()),
    path('map/', Map.as_view()),
    path('map/track.geojson', TrackGeojson.as_view()),
    path('get/photo/<str:md5>', GetPhoto.as_view())
]
