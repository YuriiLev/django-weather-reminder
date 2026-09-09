from rest_framework import permissions, viewsets

from .models import Subscription
from .permissions import IsOwner
from .serializers import SubscriptionSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related("city")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
