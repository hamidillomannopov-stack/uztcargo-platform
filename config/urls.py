from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'UZT Cargo Django Admin'
admin.site.site_title = 'UZT Cargo'
admin.site.index_title = 'Django Admin'

urlpatterns = [
    path('', include('core.urls')),
    path('api/', include('logistics.api_urls')),
    path('django-admin/', admin.site.urls),
]
