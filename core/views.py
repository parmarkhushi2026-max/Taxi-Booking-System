from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def index(request):
    """Public home view."""
    return render(request, 'core/index.html')


def admin_login_view(request):
    """
    Manual Admin Login View (No Registration).
    Only users with is_staff or is_superuser permissions are authorized.
    """
    # If already logged in as admin, redirect directly to dashboard
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'core/admin_login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Enforce admin privilege check
            if user.is_staff or user.is_superuser:
                login(request, user)
                if not remember_me:
                    # Session expires on browser close
                    request.session.set_expiry(0)
                messages.success(request, f'Signed in successfully as {user.username}.')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Access denied: You do not have administrator permissions.')
        else:
            messages.error(request, 'Invalid credentials. Please verify your username and password.')

    return render(request, 'core/admin_login.html')


@login_required(login_url='admin_login')
def admin_dashboard_view(request):
    """
    Admin Dashboard protected view.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    return render(request, 'core/admin_dashboard.html')


def admin_logout_view(request):
    """Admin logout view."""
    logout(request)
    messages.info(request, 'You have been successfully signed out.')
    return redirect('admin_login')
