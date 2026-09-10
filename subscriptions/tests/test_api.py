import pytest
from django.urls import reverse

from subscriptions.models import Subscription


@pytest.mark.django_db
class TestSubscriptionCRUD:
    def test_create(self, auth_client, city):
        response = auth_client.post(
            reverse("subscription-list"),
            {"city": city.id, "period_hours": 6, "delivery_method": "email"},
            format="json",
        )

        assert response.status_code == 201
        assert Subscription.objects.count() == 1

    def test_owner_set_from_request(self, auth_client, user, city):
        auth_client.post(
            reverse("subscription-list"),
            {"city": city.id, "period_hours": 6},
            format="json",
        )

        assert Subscription.objects.first().user == user

    def test_list_returns_own(self, auth_client, subscription):
        response = auth_client.get(reverse("subscription-list"))

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_update_period(self, auth_client, subscription):
        response = auth_client.patch(
            reverse("subscription-detail", args=[subscription.id]),
            {"period_hours": 12},
            format="json",
        )

        subscription.refresh_from_db()
        assert response.status_code == 200
        assert subscription.period_hours == 12

    def test_delete(self, auth_client, subscription):
        response = auth_client.delete(reverse("subscription-detail", args=[subscription.id]))

        assert response.status_code == 204
        assert Subscription.objects.count() == 0


@pytest.mark.django_db
class TestOwnershipIsolation:
    def test_other_users_subscription_hidden_from_list(self, api_client, other_user, subscription):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(reverse("subscription-list"))

        assert response.data["count"] == 0

    def test_other_users_subscription_returns_404(self, api_client, other_user, subscription):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(reverse("subscription-detail", args=[subscription.id]))

        assert response.status_code == 404

    def test_other_user_cannot_delete(self, api_client, other_user, subscription):
        api_client.force_authenticate(user=other_user)
        response = api_client.delete(reverse("subscription-detail", args=[subscription.id]))

        assert response.status_code == 404
        assert Subscription.objects.count() == 1

    def test_anonymous_rejected(self, api_client):
        response = api_client.get(reverse("subscription-list"))

        assert response.status_code == 401


@pytest.mark.django_db
class TestValidation:
    def test_webhook_without_url_rejected(self, auth_client, city):
        response = auth_client.post(
            reverse("subscription-list"),
            {"city": city.id, "delivery_method": "webhook"},
            format="json",
        )

        assert response.status_code == 400
        assert "webhook_url" in response.data

    def test_webhook_with_url_accepted(self, auth_client, city):
        response = auth_client.post(
            reverse("subscription-list"),
            {
                "city": city.id,
                "delivery_method": "webhook",
                "webhook_url": "https://example.com/hook",
            },
            format="json",
        )

        assert response.status_code == 201

    def test_patch_to_webhook_keeps_existing_url(self, auth_client, city, user):
        subscription = Subscription.objects.create(
            user=user,
            city=city,
            delivery_method="email",
            webhook_url="https://example.com/hook",
        )

        response = auth_client.patch(
            reverse("subscription-detail", args=[subscription.id]),
            {"delivery_method": "webhook"},
            format="json",
        )

        assert response.status_code == 200
