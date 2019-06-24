from django.urls import path
from main.views import Homepage, SearchMultipleTags, Display, Random

from . import views

urlpatterns = [
    path('', Homepage.as_view()),
    path('search/tags/', SearchMultipleTags.as_view()),
    path('display/<int:photo_id>', Display.as_view()),
    path('select_random_photo/', Random.as_view())
]
