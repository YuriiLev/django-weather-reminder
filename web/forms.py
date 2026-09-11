from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User
from subscriptions.models import Subscription
from weather.models import City


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class SubscriptionForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        empty_label="Choose a city",
    )

    class Meta:
        model = Subscription
        fields = ("city", "period_hours", "delivery_method", "webhook_url")
        widgets = {
            "webhook_url": forms.URLInput(attrs={"placeholder": "https://example.com/hook"}),
        }
        labels = {
            "period_hours": "How often",
            "delivery_method": "Send by",
            "webhook_url": "Webhook URL",
        }

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("delivery_method")
        webhook_url = cleaned.get("webhook_url")

        if method == Subscription.DeliveryMethod.WEBHOOK and not webhook_url:
            self.add_error("webhook_url", "Required when sending by webhook.")

        return cleaned
