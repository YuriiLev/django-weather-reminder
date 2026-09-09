import pytest
from django.urls import reverse

from accounts.models import User


@pytest.mark.django_db
class TestRegistration:
    def test_creates_user(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == 201
        assert User.objects.filter(email="new@example.com").exists()

    def test_password_is_hashed(self, api_client):
        api_client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "TestPass123!"},
            format="json",
        )

        user = User.objects.get(email="new@example.com")
        assert user.password != "TestPass123!"
        assert user.check_password("TestPass123!")

    def test_password_not_in_response(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "TestPass123!"},
            format="json",
        )

        assert "password" not in response.data

    def test_duplicate_email_rejected(self, api_client, user):
        response = api_client.post(
            reverse("register"),
            {"email": user.email, "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == 400

    def test_weak_password_rejected(self, api_client):
        response = api_client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "123"},
            format="json",
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestTokenAuth:
    def test_returns_token_pair(self, api_client, user):
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": "TestPass123!"},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_wrong_password_rejected(self, api_client, user):
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": "WrongPass123!"},
            format="json",
        )

        assert response.status_code == 401

    def test_refresh_returns_new_access(self, api_client, user):
        tokens = api_client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": "TestPass123!"},
            format="json",
        ).data

        response = api_client.post(
            reverse("token_refresh"),
            {"refresh": tokens["refresh"]},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data
