from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Subscription
from .permissions import IsOwner
from .serializers import SubscriptionSerializer
from .tasks import process_subscriptions


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related("city")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RunNotificationsView(APIView):
    """Entry point for the external scheduler. Queues the manager task and returns."""

    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        token = request.headers.get("X-Scheduler-Token")

        if not settings.SCHEDULER_TOKEN or token != settings.SCHEDULER_TOKEN:
            return Response(
                {"detail": "Invalid scheduler token."},
                status=status.HTTP_403_FORBIDDEN,
            )

        process_subscriptions.delay()

        return Response(
            {"detail": "Notification run queued."},
            status=status.HTTP_202_ACCEPTED,
        )
