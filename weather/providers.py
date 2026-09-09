from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests


@dataclass
class WeatherData:
    temperature: float
    humidity: int
    description: str


class WeatherProvider(ABC):
    """Interface for any weather data source."""

    @abstractmethod
    def get_current(self, city) -> WeatherData:
        """Return current weather for a city."""


class OpenWeatherProvider(WeatherProvider):
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    TIMEOUT = 10

    def __init__(self, api_key):
        self.api_key = api_key

    def get_current(self, city) -> WeatherData:
        response = requests.get(
            self.BASE_URL,
            params={
                "lat": city.latitude,
                "lon": city.longitude,
                "units": "metric",
                "appid": self.api_key,
            },
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        return WeatherData(
            temperature=payload["main"]["temp"],
            humidity=payload["main"]["humidity"],
            description=payload["weather"][0]["description"],
        )
