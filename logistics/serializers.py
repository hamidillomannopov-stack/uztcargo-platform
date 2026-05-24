from rest_framework import serializers

from .models import Client, Driver, Load, Payment, TelegramProfile


class TelegramProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramProfile
        fields = '__all__'


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'


class MobileDriverSerializer(serializers.ModelSerializer):
    mobile_token = serializers.UUIDField(read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id',
            'full_name',
            'phone',
            'truck_number',
            'mobile_token',
            'current_region',
            'last_latitude',
            'last_longitude',
            'status',
        ]


class LoadSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = Load
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
