from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from weather.models import City


class Subscription(models.Model):
    class Period(models.IntegerChoices):
        HOURLY = 1, "Every hour"
        EVERY_3_HOURS = 3, "Every 3 hours"
        EVERY_6_HOURS = 6, "Every 6 hours"
        EVERY_12_HOURS = 12, "Every 12 hours"

    class DeliveryMethod(models.TextChoices):
        EMAIL = "email", "Email"
        WEBHOOK = "webhook", "Webhook"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="subscriptions")
    period_hours = models.IntegerField(choices=Period.choices, default=Period.EVERY_3_HOURS)
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.EMAIL,
    )
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "city")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} -> {self.city} every {self.period_hours}h"

    def is_due(self):
        if not self.is_active:
            return False
        if self.last_notified_at is None:
            return True
        return timezone.now() - self.last_notified_at >= timedelta(hours=self.period_hours)
