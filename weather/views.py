from rest_framework import filters, generics

from .models import City
from .serializers import CitySerializer


class CityListView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("name", "country_code")
