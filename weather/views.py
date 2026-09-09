import requests
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import City
from .serializers import CitySerializer, WeatherSnapshotSerializer
from .services import get_weather


class CityListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("name", "country_code")


class CurrentWeatherView(APIView):
    def get(self, request):
        city_id = request.query_params.get("city_id")

        if not city_id:
            return Response(
                {"city_id": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            city = City.objects.get(pk=city_id)
        except (City.DoesNotExist, ValueError):
            return Response(
                {"city_id": "City not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            snapshot = get_weather(city)
        except requests.RequestException:
            return Response(
                {"detail": "Weather provider is unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(WeatherSnapshotSerializer(snapshot).data)
