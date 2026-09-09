from rest_framework import serializers

from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id",
            "city",
            "period_hours",
            "delivery_method",
            "webhook_url",
            "is_active",
            "last_notified_at",
            "created_at",
        )
        read_only_fields = ("id", "last_notified_at", "created_at")

    def validate(self, attrs):
        delivery_method = attrs.get(
            "delivery_method", getattr(self.instance, "delivery_method", None)
        )
        webhook_url = attrs.get("webhook_url", getattr(self.instance, "webhook_url", ""))

        if delivery_method == Subscription.DeliveryMethod.WEBHOOK and not webhook_url:
            raise serializers.ValidationError(
                {"webhook_url": "This field is required when delivery method is webhook."}
            )

        return attrs
