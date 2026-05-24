from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/loads/', views.load_list, name='load_list'),
    path('dashboard/loads/new/', views.load_create, name='load_create'),
    path('dashboard/drivers/', views.driver_list, name='driver_list'),
    path('dashboard/clients/', views.client_list, name='client_list'),
    path('login/', LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
