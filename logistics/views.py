from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Client, Driver, Load, Payment, TelegramProfile
from .serializers import (
    ClientSerializer,
    DriverSerializer,
    LoadSerializer,
    MobileDriverSerializer,
    PaymentSerializer,
    TelegramProfileSerializer,
)

REGION_COORDS = {
    'toshkent_shahri': (41.3111, 69.2797),
    'toshkent': (41.0, 69.0),
    'andijon': (40.7821, 72.3442),
    'fargona': (40.3894, 71.7848),
    'namangan': (41.0011, 71.6683),
    'sirdaryo': (40.8436, 68.6617),
    'jizzax': (40.1158, 67.8422),
    'samarqand': (39.6270, 66.9750),
    'qashqadaryo': (38.8610, 65.7847),
    'surxondaryo': (37.9409, 67.5709),
    'buxoro': (39.7670, 64.4230),
    'navoiy': (40.0844, 65.3792),
    'xorazm': (41.3565, 60.8567),
    'qoraqalpogiston': (42.4619, 59.6166),
}


def nearest_region(latitude, longitude):
    best_key = ''
    best_distance = None
    for key, (region_lat, region_lon) in REGION_COORDS.items():
        distance = (float(latitude) - region_lat) ** 2 + (float(longitude) - region_lon) ** 2
        if best_distance is None or distance < best_distance:
            best_key = key
            best_distance = distance
    return best_key


def get_mobile_driver(request):
    token = request.headers.get('X-Driver-Token') or request.data.get('mobile_token') or request.query_params.get('mobile_token')
    if not token:
        return None
    return Driver.objects.filter(mobile_token=token, is_active=True).first()


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


@api_view(['POST'])
def mobile_driver_register(request):
    phone = (request.data.get('phone') or '').strip()
    full_name = (request.data.get('full_name') or '').strip()
    truck_number = (request.data.get('truck_number') or '').strip()

    if not phone or not full_name:
        return Response({'detail': 'full_name va phone majburiy'}, status=status.HTTP_400_BAD_REQUEST)

    driver, _ = Driver.objects.update_or_create(
        phone=phone,
        defaults={
            'full_name': full_name,
            'truck_number': truck_number,
            'status': 'approved',
            'is_active': True,
        },
    )
    return Response(MobileDriverSerializer(driver).data)


@api_view(['GET'])
def mobile_driver_me(request):
    driver = get_mobile_driver(request)
    if not driver:
        return Response({'detail': 'Haydovchi topilmadi'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(MobileDriverSerializer(driver).data)


@api_view(['POST'])
def mobile_driver_location(request):
    driver = get_mobile_driver(request)
    if not driver:
        return Response({'detail': 'Haydovchi topilmadi'}, status=status.HTTP_401_UNAUTHORIZED)

    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    if latitude is None or longitude is None:
        return Response({'detail': 'latitude va longitude majburiy'}, status=status.HTTP_400_BAD_REQUEST)

    region = nearest_region(latitude, longitude)
    driver.last_latitude = Decimal(str(latitude))
    driver.last_longitude = Decimal(str(longitude))
    driver.current_region = region
    driver.save(update_fields=['last_latitude', 'last_longitude', 'current_region'])
    return Response(MobileDriverSerializer(driver).data)


@api_view(['GET'])
def mobile_active_loads(request):
    queryset = Load.objects.filter(status='new').order_by('-created_at')
    driver = get_mobile_driver(request)
    if request.query_params.get('near') == '1' and driver and driver.current_region:
        queryset = queryset.filter(from_region=driver.current_region)
    return Response(LoadSerializer(queryset[:30], many=True).data)


@api_view(['GET'])
def mobile_my_loads(request):
    driver = get_mobile_driver(request)
    if not driver:
        return Response({'detail': 'Haydovchi topilmadi'}, status=status.HTTP_401_UNAUTHORIZED)
    queryset = Load.objects.filter(driver=driver).exclude(status='cancelled').order_by('-updated_at')
    return Response(LoadSerializer(queryset, many=True).data)


@api_view(['POST'])
def mobile_accept_load(request, pk):
    driver = get_mobile_driver(request)
    if not driver:
        return Response({'detail': 'Avval ro‘yxatdan o‘ting'}, status=status.HTTP_401_UNAUTHORIZED)

    load = Load.objects.filter(pk=pk).first()
    if not load:
        return Response({'detail': 'Yuk topilmadi'}, status=status.HTTP_404_NOT_FOUND)
    if load.status != 'new' or load.driver_id:
        return Response({'detail': 'Yuk qabul qilingan'}, status=status.HTTP_409_CONFLICT)

    load.driver = driver
    load.status = 'assigned'
    load.save(update_fields=['driver', 'status', 'updated_at'])
    return Response(LoadSerializer(load).data)
