from datetime import timedelta

from django.db import models
from django.utils import timezone


class City(models.Model):
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "cities"
        unique_together = ("name", "country_code")
        ordering = ("name",)

    def __str__(self):
        return f"{self.name}, {self.country_code}"


class WeatherSnapshot(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="snapshots")
    temperature = models.FloatField()
    humidity = models.IntegerField()
    description = models.CharField(max_length=200)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fetched_at",)

    def __str__(self):
        return f"{self.city} at {self.fetched_at:%Y-%m-%d %H:%M}"

    def is_fresh(self, minutes=30):
        return timezone.now() - self.fetched_at < timedelta(minutes=minutes)
