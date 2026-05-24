from django import forms

from .models import Load


class LoadForm(forms.ModelForm):
    class Meta:
        model = Load
        fields = [
            'title',
            'client',
            'driver',
            'from_region',
            'to_region',
            'from_city',
            'to_city',
            'cargo_type',
            'vehicle_type',
            'cargo_volume',
            'weight_tons',
            'weight_text',
            'price_type',
            'price_text',
            'contact_phone',
            'client_price',
            'driver_price',
            'status',
            'notes',
        ]
