from .models import Subscription
from .notifiers import EmailNotifier, WebhookNotifier

NOTIFIERS = {
    Subscription.DeliveryMethod.EMAIL: EmailNotifier,
    Subscription.DeliveryMethod.WEBHOOK: WebhookNotifier,
}


def dispatch(subscription, snapshot):
    """Send a weather update using the subscription's delivery method."""
    notifier_class = NOTIFIERS.get(subscription.delivery_method)

    if notifier_class is None:
        raise ValueError(f"Unknown delivery method: {subscription.delivery_method}")

    notifier_class().send(subscription, snapshot)
