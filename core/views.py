from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from logistics.forms import LoadForm
from logistics.models import Client, Driver, Load, TelegramProfile


def home(request):
    stats = {
        'loads': Load.objects.count(),
        'drivers': Driver.objects.filter(is_active=True).count(),
        'clients': Client.objects.count(),
    }
    return render(request, 'site/home.html', {'stats': stats})


@login_required
def dashboard(request):
    manual_loads = Load.objects.filter(created_by_profile__isnull=True)
    loads = manual_loads.select_related('client', 'driver').order_by('-created_at')[:10]
    bot_users = TelegramProfile.objects.filter(is_active=True)
    stats = {
        'loads': manual_loads.count(),
        'active_loads': manual_loads.exclude(status__in=['delivered', 'cancelled']).count(),
        'drivers': Driver.objects.filter(is_active=True).count(),
        'clients': Client.objects.count(),
        'bot_users': bot_users.count(),
        'cargo_owners': bot_users.filter(role='cargo_owner').count(),
        'bot_drivers': bot_users.filter(role='driver').count(),
        'logists': bot_users.filter(role='logist').count(),
    }
    return render(request, 'dashboard/index.html', {'loads': loads, 'stats': stats})


@login_required
def load_list(request):
    loads = Load.objects.filter(created_by_profile__isnull=True).select_related('client', 'driver').order_by('-created_at')
    return render(request, 'dashboard/load_list.html', {'loads': loads})


@login_required
def load_create(request):
    form = LoadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('load_list')
    return render(request, 'dashboard/load_form.html', {'form': form})


@login_required
def driver_list(request):
    drivers = Driver.objects.order_by('-created_at')
    return render(request, 'dashboard/driver_list.html', {'drivers': drivers})


@login_required
def client_list(request):
    clients = Client.objects.order_by('-created_at')
    return render(request, 'dashboard/client_list.html', {'clients': clients})
