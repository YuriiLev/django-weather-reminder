from unittest.mock import patch

import pytest
import requests
from django.urls import reverse

from weather.models import WeatherSnapshot
from weather.providers import WeatherData
from weather.services import get_weather

FAKE_WEATHER = WeatherData(temperature=15.0, humidity=70, description="light rain")


@pytest.mark.django_db
class TestGetWeatherService:
    @patch("weather.services.get_provider")
    def test_fetches_when_no_snapshot(self, mock_provider, city):
        mock_provider.return_value.get_current.return_value = FAKE_WEATHER

        snapshot = get_weather(city)

        assert snapshot.temperature == 15.0
        assert WeatherSnapshot.objects.count() == 1
        mock_provider.return_value.get_current.assert_called_once_with(city)

    @patch("weather.services.get_provider")
    def test_uses_cache_when_fresh(self, mock_provider, city, snapshot):
        result = get_weather(city)

        assert result.id == snapshot.id
        assert WeatherSnapshot.objects.count() == 1
        mock_provider.return_value.get_current.assert_not_called()

    @patch("weather.services.get_provider")
    def test_refetches_when_stale(self, mock_provider, city, snapshot, settings):
        settings.WEATHER_CACHE_MINUTES = 0
        mock_provider.return_value.get_current.return_value = FAKE_WEATHER

        result = get_weather(city)

        assert result.id != snapshot.id
        assert WeatherSnapshot.objects.count() == 2


@pytest.mark.django_db
class TestCityListEndpoint:
    def test_lists_cities(self, auth_client, city):
        response = auth_client.get(reverse("city-list"))

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_search_filters(self, auth_client, city):
        response = auth_client.get(reverse("city-list"), {"search": "warsa"})

        assert response.data["count"] == 1

    def test_search_no_match(self, auth_client, city):
        response = auth_client.get(reverse("city-list"), {"search": "tokyo"})

        assert response.data["count"] == 0

    def test_requires_auth(self, api_client):
        response = api_client.get(reverse("city-list"))

        assert response.status_code == 401


@pytest.mark.django_db
class TestWeatherEndpoint:
    def test_returns_weather(self, auth_client, city, snapshot):
        response = auth_client.get(reverse("current-weather"), {"city_id": city.id})

        assert response.status_code == 200
        assert response.data["temperature"] == 20.5
        assert response.data["city"]["name"] == "Warsaw"

    def test_missing_city_id(self, auth_client):
        response = auth_client.get(reverse("current-weather"))

        assert response.status_code == 400

    def test_unknown_city(self, auth_client):
        response = auth_client.get(reverse("current-weather"), {"city_id": 9999})

        assert response.status_code == 404

    def test_invalid_city_id(self, auth_client):
        response = auth_client.get(reverse("current-weather"), {"city_id": "abc"})

        assert response.status_code == 404

    @patch("weather.services.get_provider")
    def test_provider_failure_returns_502(self, mock_provider, auth_client, city):
        mock_provider.return_value.get_current.side_effect = requests.RequestException

        response = auth_client.get(reverse("current-weather"), {"city_id": city.id})

        assert response.status_code == 502
