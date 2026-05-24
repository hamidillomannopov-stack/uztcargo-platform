from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ClientViewSet,
    DriverViewSet,
    LoadViewSet,
    PaymentViewSet,
    TelegramProfileViewSet,
    mobile_accept_load,
    mobile_active_loads,
    mobile_driver_location,
    mobile_driver_me,
    mobile_driver_register,
    mobile_my_loads,
)

router = DefaultRouter()
router.register('clients', ClientViewSet)
router.register('drivers', DriverViewSet)
router.register('loads', LoadViewSet)
router.register('payments', PaymentViewSet)
router.register('telegram-profiles', TelegramProfileViewSet)

urlpatterns = [
    path('mobile/driver/register/', mobile_driver_register),
    path('mobile/driver/me/', mobile_driver_me),
    path('mobile/driver/location/', mobile_driver_location),
    path('mobile/loads/', mobile_active_loads),
    path('mobile/loads/<int:pk>/accept/', mobile_accept_load),
    path('mobile/driver/loads/', mobile_my_loads),
]

urlpatterns += router.urls
