import random
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Sum
from .forms import (
    AdminLoginForm,
    AdminRegistrationForm,
    AdminForgotPasswordForm,
    VerifyOTPForm,
)
from .models import CustomAdmin, Driver, Vehicle, Booking


def index(request):
    """
    Public Homepage view for the Taxi Booking System.
    Handles interactive quick ride booking and displays fleet information.
    """
    new_booking = None

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        pickup_location = request.POST.get('pickup_location', '').strip()
        drop_location = request.POST.get('drop_location', '').strip()
        vehicle_type = request.POST.get('vehicle_type', 'Sedan').strip()

        fare_map = {
            'Hatchback': 300.00,
            'Sedan': 450.00,
            'SUV': 750.00,
            'Auto': 200.00,
        }
        fare = fare_map.get(vehicle_type, 450.00)

        if customer_name and customer_phone and pickup_location and drop_location:
            booking_id = f"TX-{random.randint(1000, 9999)}"
            while Booking.objects.filter(booking_id=booking_id).exists():
                booking_id = f"TX-{random.randint(1000, 9999)}"

            new_booking = Booking.objects.create(
                booking_id=booking_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                pickup_location=pickup_location,
                drop_location=drop_location,
                vehicle_type=vehicle_type,
                fare=fare,
                status='confirmed'
            )
            messages.success(
                request,
                f"🎉 Ride Booked Successfully! Your Booking ID is {booking_id}. A driver will arrive shortly."
            )
        else:
            messages.error(request, "Please fill in all booking details (Name, Phone, Pickup & Drop).")

    return render(request, 'core/index.html', {
        'new_booking': new_booking,
    })


def admin_register_view(request):
    """
    Manual Admin Registration View.
    Persists administrator accounts in the custom admin table (custom_admin_users).
    Also synchronizes with Django's User model with is_staff privileges.
    """
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            raw_password = form.cleaned_data['password']
            custom_admin = form.save(commit=False)
            custom_admin.password = make_password(raw_password)
            custom_admin.save()

            # Synchronize with Django User model for session authentication
            user, _ = User.objects.get_or_create(
                username=custom_admin.username,
                defaults={
                    'email': custom_admin.email,
                    'first_name': custom_admin.full_name,
                    'is_staff': True,
                    'is_superuser': (custom_admin.role == 'super_admin'),
                }
            )
            user.set_password(raw_password)
            user.email = custom_admin.email
            user.first_name = custom_admin.full_name
            user.is_staff = True
            if custom_admin.role == 'super_admin':
                user.is_superuser = True
            user.save()

            messages.success(
                request,
                f"Admin '{custom_admin.username}' registered successfully in the custom admin table! Please sign in."
            )
            return redirect('admin_login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AdminRegistrationForm()

    return render(request, 'core/admin_register.html', {
        'form': form,
    })


def admin_login_view(request):
    """
    Admin Login view supporting both custom admin table (custom_admin_users)
    and Django's native authentication framework.
    """
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    redirect_to = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        # Check in custom admin table first
        custom_admin = CustomAdmin.objects.filter(username__iexact=username, is_active=True).first()

        if custom_admin and check_password(password, custom_admin.password):
            django_user, _ = User.objects.get_or_create(
                username=custom_admin.username,
                defaults={
                    'email': custom_admin.email,
                    'first_name': custom_admin.full_name,
                    'is_staff': True,
                    'is_superuser': (custom_admin.role == 'super_admin'),
                }
            )
            django_user.set_password(password)
            django_user.is_staff = True
            if custom_admin.role == 'super_admin':
                django_user.is_superuser = True
            django_user.save()

            login(request, django_user)
            custom_admin.last_login = timezone.now()
            custom_admin.save(update_fields=['last_login'])

            if not remember_me:
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {custom_admin.full_name}!')

            if redirect_to and url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(redirect_to)
            return redirect('admin_dashboard')

        # Fallback to standard Django authentication
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


def admin_forgot_password_view(request):
    """
    Forgot Password view for Administrator Accounts.
    Accepts the admin's email and generates a 6-digit OTP using the Python random library.
    """
    if request.method == 'POST':
        form = AdminForgotPasswordForm(request.POST)
        if form.is_valid():
            target_email = form.cleaned_data['email'].strip().lower()

            # Verify admin existence in custom admin table or User model
            admin_found = (
                CustomAdmin.objects.filter(email__iexact=target_email).exists() or
                User.objects.filter(email__iexact=target_email, is_staff=True).exists()
            )

            if admin_found:
                # Generate 6-digit secure OTP using Python random library
                otp = f"{random.randint(100000, 999999)}"

                # Store OTP and metadata in session
                request.session['reset_email'] = target_email
                request.session['reset_otp'] = otp
                request.session['otp_timestamp'] = timezone.now().timestamp()
                request.session['otp_verified'] = False

                messages.success(
                    request,
                    f"A 6-digit OTP ({otp}) has been generated for {target_email} using the random library."
                )
                return redirect('admin_verify_otp')
            else:
                messages.error(
                    request,
                    f"No administrator account is registered with the email: {target_email}."
                )
    else:
        form = AdminForgotPasswordForm()

    return render(request, 'core/admin_forgot_password.html', {
        'form': form,
    })


def admin_verify_otp_view(request):
    """
    OTP Verification View for Password Reset.
    Validates the 6-digit OTP generated via random library.
    """
    email = request.session.get('reset_email')
    expected_otp = request.session.get('reset_otp')

    if not email or not expected_otp:
        messages.error(request, "Session expired or missing. Please initiate password reset again.")
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            submitted_otp = form.cleaned_data['otp'].strip()

            # Check if OTP expired (10 minutes = 600 seconds)
            otp_time = request.session.get('otp_timestamp', 0)
            if timezone.now().timestamp() - otp_time > 600:
                messages.error(request, "The OTP has expired (valid for 10 minutes). Please request a new OTP.")
                return redirect('admin_verify_otp')

            if submitted_otp == expected_otp:
                request.session['otp_verified'] = True
                messages.success(request, "OTP verified successfully! Please create your new password.")
                return redirect('admin_reset_password')
            else:
                messages.error(request, "Invalid OTP code. Please enter the correct 6-digit OTP.")
    else:
        form = VerifyOTPForm()

    return render(request, 'core/admin_verify_otp.html', {
        'form': form,
        'email': email,
        'current_otp': expected_otp,  # Displayed in UI banner for immediate ease of testing
    })


def admin_resend_otp_view(request):
    """
    Resends/Regenerates a fresh 6-digit OTP using Python's random library.
    """
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "Please enter your email first to generate an OTP.")
        return redirect('admin_forgot_password')

    # Generate fresh OTP using random library
    new_otp = f"{random.randint(100000, 999999)}"
    request.session['reset_otp'] = new_otp
    request.session['otp_timestamp'] = timezone.now().timestamp()
    request.session['otp_verified'] = False

    messages.success(request, f"New 6-digit OTP ({new_otp}) generated successfully!")
    return redirect('admin_verify_otp')


def admin_reset_password_view(request):
    """
    Password Reset confirmation view.
    Allows administrators to set a new password after verifying the random OTP.
    """
    email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified', False)

    # Protect route: must have verified OTP first
    if not email or not otp_verified:
        messages.error(request, "Access denied. Please verify your OTP code first.")
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password or not confirm_password:
            messages.error(request, "Please enter both password fields.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        else:
            updated = False

            # Update custom admin table
            custom_admin = CustomAdmin.objects.filter(email__iexact=email).first()
            if custom_admin:
                custom_admin.password = make_password(new_password)
                custom_admin.save(update_fields=['password'])
                updated = True

            # Update Django User model
            user = User.objects.filter(email__iexact=email).first()
            if user:
                user.set_password(new_password)
                user.save()
                updated = True

            if updated:
                # Clear password reset session state
                for key in ['reset_email', 'reset_otp', 'otp_timestamp', 'otp_verified']:
                    request.session.pop(key, None)

                messages.success(
                    request,
                    "Password has been reset successfully! Please sign in with your new password."
                )
                return redirect('admin_login')
            else:
                messages.error(request, "Unable to find an account for the provided email.")

    return render(request, 'core/admin_reset_password.html', {
        'email': email,
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
    total_custom_admins = CustomAdmin.objects.count()
    revenue_agg = Booking.objects.filter(status='completed').aggregate(Sum('fare'))
    total_revenue = revenue_agg['fare__sum'] or 0

    recent_bookings = Booking.objects.all()[:8]
    drivers = Driver.objects.all()[:5]

    context = {
        'total_bookings': total_bookings,
        'active_rides': active_rides,
        'available_drivers': available_drivers,
        'total_vehicles': total_vehicles,
        'total_custom_admins': total_custom_admins,
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
