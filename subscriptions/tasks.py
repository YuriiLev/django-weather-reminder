import logging

from celery import shared_task
from django.utils import timezone

from weather.services import get_weather

from .dispatcher import dispatch
from .models import Subscription

logger = logging.getLogger(__name__)


@shared_task
def process_subscriptions():
    """Find every subscription that is due and queue a notification for each."""
    queued = 0

    for subscription in Subscription.objects.filter(is_active=True).select_related("city", "user"):
        if subscription.is_due():
            notify_one.delay(subscription.id)
            queued += 1

    logger.info("Queued %s notifications", queued)
    return queued


@shared_task
def notify_one(subscription_id):
    """Send one notification and record the time only if it succeeded."""
    try:
        subscription = Subscription.objects.select_related("city", "user").get(pk=subscription_id)
    except Subscription.DoesNotExist:
        logger.warning("Subscription %s no longer exists", subscription_id)
        return

    snapshot = get_weather(subscription.city)
    dispatch(subscription, snapshot)

    subscription.last_notified_at = timezone.now()
    subscription.save(update_fields=["last_notified_at"])
