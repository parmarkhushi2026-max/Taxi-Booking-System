from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import AdminLoginForm


def index(request):
    """Public home view."""
    return render(request, 'core/index.html')


def admin_login_view(request):
    """
    Admin Login view using Django's built-in authentication system.
    Authenticates against Django's User model and enforces admin (staff/superuser) status.
    No registration allowed.
    """
    # Redirect if already logged in as admin
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    redirect_to = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Session handling for remember_me
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # expires on browser close

            messages.success(request, f'Welcome back, {user.username}!')

            # Validate redirect URL for security
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
    Admin Dashboard protected view.
    Only accessible to authenticated administrators.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    return render(request, 'core/admin_dashboard.html')


def admin_logout_view(request):
    """
    Admin Logout view using Django authentication.
    Clears the session and redirects to admin login.
    """
    logout(request)
    messages.info(request, 'You have been successfully signed out.')
    return redirect('admin_login')
