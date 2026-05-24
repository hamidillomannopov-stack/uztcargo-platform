from rest_framework import viewsets

from .models import Client, Driver, Load, Payment, TelegramProfile
from .serializers import (
    ClientSerializer,
    DriverSerializer,
    LoadSerializer,
    PaymentSerializer,
    TelegramProfileSerializer,
)


class TelegramProfileViewSet(viewsets.ModelViewSet):
    queryset = TelegramProfile.objects.all().order_by('-created_at')
    serializer_class = TelegramProfileSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all().order_by('-created_at')
    serializer_class = DriverSerializer


class LoadViewSet(viewsets.ModelViewSet):
    queryset = Load.objects.select_related('client', 'driver').all().order_by('-created_at')
    serializer_class = LoadSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('load').all().order_by('-created_at')
    serializer_class = PaymentSerializer
