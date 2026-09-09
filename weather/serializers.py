from rest_framework import serializers

from .models import City, WeatherSnapshot


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "country_code", "latitude", "longitude")


class WeatherSnapshotSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = WeatherSnapshot
        fields = ("city", "temperature", "humidity", "description", "fetched_at")
