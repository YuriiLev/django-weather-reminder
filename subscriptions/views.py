from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Subscription
from .permissions import IsOwner
from .serializers import SubscriptionSerializer
from .tasks import process_subscriptions

ID_PARAMETER = OpenApiParameter(
    "id",
    OpenApiTypes.INT,
    OpenApiParameter.PATH,
    description="ID of the subscription.",
)


@extend_schema_view(
    retrieve=extend_schema(parameters=[ID_PARAMETER]),
    update=extend_schema(parameters=[ID_PARAMETER]),
    partial_update=extend_schema(parameters=[ID_PARAMETER]),
    destroy=extend_schema(parameters=[ID_PARAMETER]),
)
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

    @extend_schema(
        summary="Trigger a notification run",
        description=(
            "Called by an external scheduler. Queues the task that finds due "
            "subscriptions and sends notifications. Requires a shared secret header."
        ),
        parameters=[
            OpenApiParameter(
                name="X-Scheduler-Token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Shared secret configured as SCHEDULER_TOKEN.",
            )
        ],
        request=None,
        responses={202: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
    )
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
