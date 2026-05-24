from decimal import Decimal

from django.db import models

UZBEKISTAN_REGIONS = [
    ('toshkent_shahri', 'Toshkent shahri'),
    ('toshkent', 'Toshkent viloyati'),
    ('andijon', 'Andijon'),
    ('fargona', "Farg'ona"),
    ('namangan', 'Namangan'),
    ('sirdaryo', 'Sirdaryo'),
    ('jizzax', 'Jizzax'),
    ('samarqand', 'Samarqand'),
    ('qashqadaryo', 'Qashqadaryo'),
    ('surxondaryo', 'Surxondaryo'),
    ('buxoro', 'Buxoro'),
    ('navoiy', 'Navoiy'),
    ('xorazm', 'Xorazm'),
    ('qoraqalpogiston', "Qoraqalpog'iston"),
]


class TelegramProfile(models.Model):
    ROLE_CHOICES = [
        ('cargo_owner', 'Yuk egasi'),
        ('driver', 'Haydovchi'),
        ('logist', 'Logist'),
    ]

    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    company_name = models.CharField(max_length=255, blank=True)
    truck_number = models.CharField(max_length=50, blank=True)
    driver = models.OneToOneField('Driver', on_delete=models.SET_NULL, null=True, blank=True)
    last_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    current_region = models.CharField(max_length=40, choices=UZBEKISTAN_REGIONS, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def contact_line(self):
        username = f'@{self.username}' if self.username else ''
        parts = [self.full_name, self.phone, username]
        return ' | '.join([part for part in parts if part])


class Client(models.Model):
    company_name = models.CharField(max_length=255)
    manager_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Driver(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    truck_number = models.CharField(max_length=50, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Load(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PRICE_TYPE_CHOICES = [
        ('fixed', 'Summa belgilangan'),
        ('negotiable', 'Kelishiladi'),
    ]

    title = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_profile = models.ForeignKey(
        TelegramProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_loads',
    )
    assigned_driver_profile = models.ForeignKey(
        TelegramProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_loads',
    )
    from_region = models.CharField(max_length=40, choices=UZBEKISTAN_REGIONS, blank=True)
    to_region = models.CharField(max_length=40, choices=UZBEKISTAN_REGIONS, blank=True)
    from_city = models.CharField(max_length=120)
    to_city = models.CharField(max_length=120)
    cargo_type = models.CharField(max_length=120, blank=True)
    vehicle_type = models.CharField(max_length=120, blank=True)
    cargo_volume = models.CharField(max_length=120, blank=True)
    weight_tons = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weight_text = models.CharField(max_length=120, blank=True)
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, default='fixed')
    price_text = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    owner_contact_info = models.TextField(blank=True)
    logist_contact_info = models.TextField(blank=True)
    announcement_chat_id = models.CharField(max_length=80, blank=True)
    announcement_message_id = models.PositiveIntegerField(null=True, blank=True)
    client_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    driver_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def balance(self):
        return self.client_price - self.paid_amount

    @property
    def profit(self):
        return self.client_price - self.driver_price

    def __str__(self):
        return self.title


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank', 'Bank transfer'),
    ]

    load = models.ForeignKey(Load, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total = self.load.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        Load.objects.filter(pk=self.load_id).update(paid_amount=total)

    def __str__(self):
        return f'{self.load} - {self.amount}'
