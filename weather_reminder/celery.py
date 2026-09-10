import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weather_reminder.settings")

app = Celery("weather_reminder")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_url = os.environ.get("BROKER_URL") or app.conf.broker_url
app.autodiscover_tasks()
