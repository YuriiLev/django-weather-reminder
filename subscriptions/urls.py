from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import RunNotificationsView, SubscriptionViewSet

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls + [
    path("tasks/run-notifications/", RunNotificationsView.as_view(), name="run-notifications"),
]
