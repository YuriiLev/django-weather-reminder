from django.urls import path

from .views import CityListView, CurrentWeatherView

urlpatterns = [
    path("cities/", CityListView.as_view(), name="city-list"),
    path("weather/", CurrentWeatherView.as_view(), name="current-weather"),
]
