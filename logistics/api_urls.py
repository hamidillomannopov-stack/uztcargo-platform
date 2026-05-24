from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, DriverViewSet, LoadViewSet, PaymentViewSet, TelegramProfileViewSet

router = DefaultRouter()
router.register('clients', ClientViewSet)
router.register('drivers', DriverViewSet)
router.register('loads', LoadViewSet)
router.register('payments', PaymentViewSet)
router.register('telegram-profiles', TelegramProfileViewSet)

urlpatterns = router.urls
