from django.urls import path
from main.views import Homepage, SearchMultipleTags, SearchPhotoId, SearchBox, SearchNear, Display, Random, Map,\
    PhotosGeojson, TrackGeojson, GetPhoto

from . import views

urlpatterns = [
    path('', Homepage.as_view()),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('search/id/', SearchPhotoId.as_view()),
    path('search/box/', SearchBox.as_view()),
    path('search/near', SearchNear.as_view()),
    path('display/<int:photo_id>', Display.as_view()),
    path('select_random_photo/', Random.as_view()),
    path('map/photos.geojson', PhotosGeojson.as_view()),
    path('map/', Map.as_view()),
    path('map/track.geojson', TrackGeojson.as_view()),
    path('get/photo/<str:md5>', GetPhoto.as_view())
]
