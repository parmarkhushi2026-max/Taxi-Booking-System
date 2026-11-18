from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Sum
from .forms import AdminLoginForm
from .models import Driver, Vehicle, Booking


def index(request):
    """Public home view."""
    return render(request, 'core/index.html')


def admin_login_view(request):
    """
    Admin Login view using Django's built-in authentication system.
    Authenticates against Django's User model and enforces admin (staff/superuser) status.
    No registration allowed.
    """
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    redirect_to = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {user.username}!')

            if redirect_to and url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(redirect_to)
            return redirect('admin_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AdminLoginForm(request)

    return render(request, 'core/admin_login.html', {
        'form': form,
        'next': redirect_to
    })


@login_required(login_url='admin_login')
def admin_dashboard_view(request):
    """
    Basic Admin Dashboard protected view that loads after admin login.
    Displays taxi booking metrics, recent trips, and driver statuses.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    total_bookings = Booking.objects.count()
    active_rides = Booking.objects.filter(status__in=['ongoing', 'confirmed']).count()
    available_drivers = Driver.objects.filter(status='available').count()
    total_vehicles = Vehicle.objects.filter(is_active=True).count()
    revenue_agg = Booking.objects.filter(status='completed').aggregate(Sum('fare'))
    total_revenue = revenue_agg['fare__sum'] or 0

    recent_bookings = Booking.objects.all()[:8]
    drivers = Driver.objects.all()[:5]

    context = {
        'total_bookings': total_bookings,
        'active_rides': active_rides,
        'available_drivers': available_drivers,
        'total_vehicles': total_vehicles,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'drivers': drivers,
    }

    return render(request, 'core/admin_dashboard.html', context)


def admin_logout_view(request):
    """
    Admin Logout view using Django authentication.
    Clears the session and redirects to admin login.
    """
    logout(request)
    messages.info(request, 'You have been successfully signed out.')
    return redirect('admin_login')
