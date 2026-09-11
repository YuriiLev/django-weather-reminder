import pytest
from rest_framework.test import APIClient

from accounts.models import User
from subscriptions.models import Subscription
from weather.models import City, WeatherSnapshot


@pytest.fixture(autouse=True)
def use_plain_static_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="TestPass123!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@example.com", password="TestPass123!")


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def city(db):
    return City.objects.create(
        name="Warsaw",
        country_code="PL",
        latitude=52.2297,
        longitude=21.0122,
    )


@pytest.fixture
def subscription(db, user, city):
    return Subscription.objects.create(user=user, city=city, period_hours=3)


@pytest.fixture
def snapshot(db, city):
    return WeatherSnapshot.objects.create(
        city=city,
        temperature=20.5,
        humidity=60,
        description="clear sky",
    )
