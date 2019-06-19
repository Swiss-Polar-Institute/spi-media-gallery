from django.urls import path
from main.views import Homepage, Search, SearchMultipleTags, Display

from . import views

urlpatterns = [
    path('', Homepage.as_view()),
    path('search/tag/<int:tag_id>', Search.as_view()),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('display/<int:photo_id>', Display.as_view())
]
