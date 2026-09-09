from django.conf import settings

from .models import WeatherSnapshot
from .providers import OpenWeatherProvider


def get_provider():
    return OpenWeatherProvider(api_key=settings.WEATHER_API_KEY)


def get_weather(city):
    """Return current weather for a city, using a cached snapshot when fresh."""
    snapshot = city.snapshots.first()

    if snapshot and snapshot.is_fresh(minutes=settings.WEATHER_CACHE_MINUTES):
        return snapshot

    data = get_provider().get_current(city)

    return WeatherSnapshot.objects.create(
        city=city,
        temperature=data.temperature,
        humidity=data.humidity,
        description=data.description,
    )
