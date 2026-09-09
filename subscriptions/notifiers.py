from abc import ABC, abstractmethod

import requests
from django.conf import settings
from django.core.mail import send_mail


class Notifier(ABC):
    """Interface for any notification delivery channel."""

    @abstractmethod
    def send(self, subscription, snapshot):
        """Deliver a weather update for a subscription."""


class EmailNotifier(Notifier):
    def send(self, subscription, snapshot):
        send_mail(
            subject=self._build_subject(snapshot),
            message=self._build_message(subscription, snapshot),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.user.email],
        )

    def _build_subject(self, snapshot):
        return f"Weather in {snapshot.city.name}: {snapshot.temperature:.0f}°C"

    def _build_message(self, subscription, snapshot):
        return (
            f"Current weather in {snapshot.city}:\n\n"
            f"Temperature: {snapshot.temperature:.1f}°C\n"
            f"Humidity: {snapshot.humidity}%\n"
            f"Conditions: {snapshot.description}\n\n"
            f"You receive this every {subscription.period_hours} hours."
        )


class WebhookNotifier(Notifier):
    TIMEOUT = 10

    def send(self, subscription, snapshot):
        response = requests.post(
            subscription.webhook_url,
            json=self._build_payload(snapshot),
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()

    def _build_payload(self, snapshot):
        return {
            "city": snapshot.city.name,
            "country_code": snapshot.city.country_code,
            "temperature": snapshot.temperature,
            "humidity": snapshot.humidity,
            "description": snapshot.description,
            "fetched_at": snapshot.fetched_at.isoformat(),
        }
