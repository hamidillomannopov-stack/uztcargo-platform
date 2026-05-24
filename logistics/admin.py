from django.contrib import admin

from .models import Client, Driver, Load, Payment, TelegramProfile


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'role', 'phone', 'username', 'current_region', 'is_active', 'updated_at')
    list_filter = ('role', 'current_region', 'is_active')
    search_fields = ('full_name', 'phone', 'username', 'company_name', 'truck_number')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'manager_name', 'phone', 'created_at')
    search_fields = ('company_name', 'manager_name', 'phone')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'truck_number', 'current_region', 'status', 'is_active')
    list_filter = ('status', 'is_active', 'current_region')
    search_fields = ('full_name', 'phone', 'truck_number')


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'from_region',
        'to_region',
        'created_by_profile',
        'assigned_driver_profile',
        'status',
        'price_label',
        'contact_phone',
        'created_at',
    )
    list_filter = ('status', 'from_region', 'to_region', 'price_type')
    search_fields = ('title', 'from_city', 'to_city', 'cargo_type', 'vehicle_type', 'contact_phone')
    inlines = [PaymentInline]

    def price_label(self, obj):
        return obj.price_text or obj.get_price_type_display()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('load', 'amount', 'method', 'created_at')
    list_filter = ('method',)
