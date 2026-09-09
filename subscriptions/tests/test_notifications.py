from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
from django.utils import timezone

from subscriptions.dispatcher import dispatch
from subscriptions.models import Subscription
from subscriptions.notifiers import EmailNotifier, WebhookNotifier
from subscriptions.tasks import notify_one, process_subscriptions


@pytest.mark.django_db
class TestIsDue:
    def test_never_notified_is_due(self, subscription):
        assert subscription.is_due() is True

    def test_recently_notified_is_not_due(self, subscription):
        subscription.last_notified_at = timezone.now()
        assert subscription.is_due() is False

    def test_period_elapsed_is_due(self, subscription):
        subscription.last_notified_at = timezone.now() - timedelta(hours=4)
        assert subscription.is_due() is True

    def test_inactive_is_never_due(self, subscription):
        subscription.is_active = False
        assert subscription.is_due() is False


@pytest.mark.django_db
class TestNotifiers:
    @patch("subscriptions.notifiers.send_mail")
    def test_email_sends_to_subscriber(self, mock_send, subscription, snapshot):
        EmailNotifier().send(subscription, snapshot)

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["recipient_list"] == [subscription.user.email]

    @patch("subscriptions.notifiers.send_mail")
    def test_email_body_contains_weather(self, mock_send, subscription, snapshot):
        EmailNotifier().send(subscription, snapshot)

        body = mock_send.call_args.kwargs["message"]
        assert "20.5" in body
        assert "clear sky" in body

    @patch("subscriptions.notifiers.requests.post")
    def test_webhook_posts_payload(self, mock_post, subscription, snapshot):
        subscription.webhook_url = "https://example.com/hook"

        WebhookNotifier().send(subscription, snapshot)

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["city"] == "Warsaw"
        assert payload["temperature"] == 20.5


@pytest.mark.django_db
class TestDispatcher:
    @patch("subscriptions.notifiers.send_mail")
    def test_dispatches_email(self, mock_send, subscription, snapshot):
        dispatch(subscription, snapshot)

        mock_send.assert_called_once()

    @patch("subscriptions.notifiers.requests.post")
    def test_dispatches_webhook(self, mock_post, subscription, snapshot):
        subscription.delivery_method = Subscription.DeliveryMethod.WEBHOOK
        subscription.webhook_url = "https://example.com/hook"

        dispatch(subscription, snapshot)

        mock_post.assert_called_once()

    def test_unknown_method_raises(self, subscription, snapshot):
        subscription.delivery_method = "carrier_pigeon"

        with pytest.raises(ValueError):
            dispatch(subscription, snapshot)


@pytest.mark.django_db
class TestTasks:
    @patch("subscriptions.tasks.notify_one.delay")
    def test_queues_due_subscriptions(self, mock_delay, subscription):
        queued = process_subscriptions()

        assert queued == 1
        mock_delay.assert_called_once_with(subscription.id)

    @patch("subscriptions.tasks.notify_one.delay")
    def test_skips_not_due(self, mock_delay, subscription):
        subscription.last_notified_at = timezone.now()
        subscription.save()

        queued = process_subscriptions()

        assert queued == 0
        mock_delay.assert_not_called()

    @patch("subscriptions.tasks.notify_one.delay")
    def test_skips_inactive(self, mock_delay, subscription):
        subscription.is_active = False
        subscription.save()

        queued = process_subscriptions()

        assert queued == 0

    @patch("subscriptions.tasks.dispatch")
    @patch("subscriptions.tasks.get_weather")
    def test_notify_one_sends_and_records(
        self, mock_weather, mock_dispatch, subscription, snapshot
    ):
        mock_weather.return_value = snapshot

        notify_one(subscription.id)

        subscription.refresh_from_db()
        mock_dispatch.assert_called_once()
        assert subscription.last_notified_at is not None

    @patch("subscriptions.tasks.dispatch")
    @patch("subscriptions.tasks.get_weather")
    def test_failed_send_does_not_record(self, mock_weather, mock_dispatch, subscription, snapshot):
        mock_weather.return_value = snapshot
        mock_dispatch.side_effect = requests.RequestException

        with pytest.raises(requests.RequestException):
            notify_one(subscription.id)

        subscription.refresh_from_db()
        assert subscription.last_notified_at is None

    def test_missing_subscription_returns_quietly(self):
        assert notify_one(99999) is None
