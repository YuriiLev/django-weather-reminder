import pytest
from django.urls import reverse

from accounts.models import User
from subscriptions.models import Subscription


@pytest.fixture
def logged_in_client(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestAccessControl:
    @pytest.mark.parametrize(
        "url_name,args",
        [
            ("web:dashboard", []),
            ("web:subscription_create", []),
        ],
    )
    def test_anonymous_redirected_to_login(self, client, url_name, args):
        response = client.get(reverse(url_name, args=args))

        assert response.status_code == 302
        assert reverse("web:login") in response.url

    def test_anonymous_redirected_from_edit(self, client, subscription):
        response = client.get(reverse("web:subscription_edit", args=[subscription.pk]))

        assert response.status_code == 302
        assert reverse("web:login") in response.url

    def test_home_renders_for_anonymous(self, client):
        response = client.get(reverse("web:home"))

        assert response.status_code == 200

    def test_home_redirects_logged_in_user(self, logged_in_client):
        response = logged_in_client.get(reverse("web:home"))

        assert response.status_code == 302
        assert response.url == reverse("web:dashboard")


@pytest.mark.django_db
class TestSignup:
    def test_creates_user_and_logs_in(self, client):
        response = client.post(
            reverse("web:signup"),
            {
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        assert response.status_code == 302
        assert User.objects.filter(email="new@example.com").exists()
        assert response.wsgi_request.user.is_authenticated

    def test_password_is_hashed(self, client):
        client.post(
            reverse("web:signup"),
            {
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        created = User.objects.get(email="new@example.com")
        assert created.password != "StrongPass123!"
        assert created.check_password("StrongPass123!")

    def test_mismatched_passwords_rejected(self, client):
        response = client.post(
            reverse("web:signup"),
            {
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "DifferentPass123!",
            },
        )

        assert response.status_code == 200
        assert not User.objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
class TestDashboard:
    def test_lists_own_subscriptions(self, logged_in_client, subscription):
        response = logged_in_client.get(reverse("web:dashboard"))

        assert response.status_code == 200
        assert list(response.context["subscriptions"]) == [subscription]

    def test_does_not_list_other_users_subscriptions(self, client, other_user, subscription):
        client.force_login(other_user)
        response = client.get(reverse("web:dashboard"))

        assert list(response.context["subscriptions"]) == []


@pytest.mark.django_db
class TestSubscriptionCreate:
    def test_creates_with_request_user_as_owner(self, logged_in_client, user, city):
        response = logged_in_client.post(
            reverse("web:subscription_create"),
            {"city": city.id, "period_hours": 6, "delivery_method": "email"},
        )

        assert response.status_code == 302
        assert Subscription.objects.get().user == user

    def test_webhook_without_url_rejected(self, logged_in_client, city):
        response = logged_in_client.post(
            reverse("web:subscription_create"),
            {"city": city.id, "period_hours": 6, "delivery_method": "webhook"},
        )

        assert response.status_code == 200
        assert Subscription.objects.count() == 0


@pytest.mark.django_db
class TestSubscriptionEdit:
    def test_updates_own_subscription(self, logged_in_client, subscription, city):
        logged_in_client.post(
            reverse("web:subscription_edit", args=[subscription.pk]),
            {"city": city.id, "period_hours": 12, "delivery_method": "email"},
        )

        subscription.refresh_from_db()
        assert subscription.period_hours == 12

    def test_other_users_subscription_returns_404(self, client, other_user, subscription):
        client.force_login(other_user)
        response = client.get(reverse("web:subscription_edit", args=[subscription.pk]))

        assert response.status_code == 404


@pytest.mark.django_db
class TestSubscriptionDelete:
    def test_deletes_own_subscription(self, logged_in_client, subscription):
        response = logged_in_client.post(reverse("web:subscription_delete", args=[subscription.pk]))

        assert response.status_code == 302
        assert Subscription.objects.count() == 0

    def test_get_does_not_delete(self, logged_in_client, subscription):
        logged_in_client.get(reverse("web:subscription_delete", args=[subscription.pk]))

        assert Subscription.objects.count() == 1

    def test_other_user_cannot_delete(self, client, other_user, subscription):
        client.force_login(other_user)
        response = client.post(reverse("web:subscription_delete", args=[subscription.pk]))

        assert response.status_code == 404
        assert Subscription.objects.count() == 1
