from django.urls import path
from main.views import Homepage, SearchResult

from . import views

urlpatterns = [
    path('', Homepage.as_view()),
    path('search_results/tag/<int:tag_id>', SearchResult.as_view()),

]
