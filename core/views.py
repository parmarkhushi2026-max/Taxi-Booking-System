import random
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.mail import send_mail
from django.conf import settings
from .forms import (
    AdminLoginForm,
    AdminRegistrationForm,
    AdminForgotPasswordForm,
    VerifyOTPForm,
    AdminResetPasswordForm,
    AppUserCreateForm,
    AppUserEditForm,
)
from .models import User as AppUser, CustomAdmin, Driver, Vehicle, Booking


def send_otp_via_console_email(target_email, otp):
    """
    Dispatches a formatted OTP recovery email to the console-based email backend.
    The message prints directly to the running server terminal console.
    """
    subject = "Taxi Booking Admin - Password Reset OTP"
    message = f"""============================================================
TAXI BOOKING SYSTEM - ADMINISTRATOR PASSWORD RECOVERY
============================================================
Hello Administrator,

A request was received to reset the password for your account:
Email: {target_email}

Your 6-Digit One-Time Password (OTP) is:
------------------------------------------------------------
>>> {otp} <<<
------------------------------------------------------------

Details:
• Validity: 10 minutes
• Method: Generated using Python random library
• Backend: Django Console Email Backend
• Destination: Printed directly to console / terminal

If you did not request this, you can safely ignore this message.
Your administrator credentials remain protected.

Best regards,
Taxi Booking Dispatch & Security Team
============================================================"""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@taxibooking.com')
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[target_email],
        fail_silently=False,
    )


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
        form = AdminRegistrationForm(request.POST, request.FILES)
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

                # Dispatch OTP email to console backend
                send_otp_via_console_email(target_email, otp)

                # Store OTP and metadata in session
                request.session['reset_email'] = target_email
                request.session['reset_otp'] = otp
                request.session['otp_timestamp'] = timezone.now().timestamp()
                request.session['otp_verified'] = False

                messages.success(
                    request,
                    f"A 6-digit OTP ({otp}) has been generated and dispatched via console-based email to {target_email}!"
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

    # Dispatch fresh OTP via console email backend
    send_otp_via_console_email(email, new_otp)

    request.session['reset_otp'] = new_otp
    request.session['otp_timestamp'] = timezone.now().timestamp()
    request.session['otp_verified'] = False

    messages.success(request, f"New 6-digit OTP ({new_otp}) dispatched via console-based email!")
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
        form = AdminResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            updated = False

            # Update custom admin table
            custom_admin = CustomAdmin.objects.filter(email__iexact=email).first()
            if custom_admin:
                custom_admin.password = make_password(new_password)
                custom_admin.save(update_fields=['password'])
                updated = True

                # Also sync corresponding Django auth User model
                django_user = User.objects.filter(username__iexact=custom_admin.username).first()
                if django_user:
                    django_user.set_password(new_password)
                    django_user.save()

            # Update Django User model if user found by email
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
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AdminResetPasswordForm()

    return render(request, 'core/admin_reset_password.html', {
        'form': form,
        'email': email,
    })


def get_admin_context(request):
    """
    Helper function to extract authenticated administrator profile details.
    """
    custom_admin = CustomAdmin.objects.filter(username__iexact=request.user.username).first()
    if not custom_admin and request.user.email:
        custom_admin = CustomAdmin.objects.filter(email__iexact=request.user.email).first()

    admin_name = custom_admin.full_name if custom_admin else (request.user.get_full_name() or request.user.username)
    admin_role = custom_admin.get_role_display() if custom_admin else ("Super Administrator" if request.user.is_superuser else "Administrator")
    admin_email = custom_admin.email if custom_admin else (request.user.email or "admin@taxibooking.com")
    admin_phone = custom_admin.phone if custom_admin else "Not specified"
    admin_profile_image = custom_admin.profile_image.url if (custom_admin and custom_admin.profile_image) else None

    return {
        'admin_name': admin_name,
        'admin_role': admin_role,
        'admin_email': admin_email,
        'admin_phone': admin_phone,
        'admin_profile_image': admin_profile_image,
        'custom_admin': custom_admin,
    }


@login_required(login_url='admin_login')
def admin_dashboard_view(request):
    """
    Basic Admin Dashboard protected view that loads after admin login.
    Displays taxi booking metrics, recent trips, driver statuses,
    admin name, and admin profile image.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    context = get_admin_context(request)
    context['active_nav'] = 'dashboard'

    total_bookings = Booking.objects.count()
    active_rides = Booking.objects.filter(status__in=['ongoing', 'confirmed']).count()
    available_drivers = Driver.objects.filter(status='available').count()
    total_vehicles = Vehicle.objects.filter(is_active=True).count()
    total_custom_admins = CustomAdmin.objects.count()
    revenue_agg = Booking.objects.filter(status='completed').aggregate(Sum('fare'))
    total_revenue = revenue_agg['fare__sum'] or 0

    recent_bookings = Booking.objects.all()[:8]
    drivers = Driver.objects.all()[:5]

    context.update({
        'total_bookings': total_bookings,
        'active_rides': active_rides,
        'available_drivers': available_drivers,
        'total_vehicles': total_vehicles,
        'total_custom_admins': total_custom_admins,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'drivers': drivers,
    })

    return render(request, 'core/admin_dashboard.html', context)


@login_required(login_url='admin_login')
def admin_drivers_view(request):
    """
    Placeholder view for future Drivers Management module.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    context = get_admin_context(request)
    context['active_nav'] = 'drivers'
    context['module_title'] = 'Drivers Management'
    context['module_icon'] = 'bi-person-badge-fill'
    context['module_description'] = 'Manage taxi fleet chauffeurs, verify driver licenses, track live shift statuses, and handle payouts.'
    context['total_drivers'] = Driver.objects.count()
    context['available_drivers'] = Driver.objects.filter(status='available').count()
    context['on_trip_drivers'] = Driver.objects.filter(status='on_trip').count()
    context['offline_drivers'] = Driver.objects.filter(status='offline').count()
    context['drivers_list'] = Driver.objects.all()[:10]

    return render(request, 'core/admin_drivers.html', context)


@login_required(login_url='admin_login')
def admin_users_view(request):
    """
    User Management and Listing page for Administrators.
    Lists all app users / customers with search, filter, status toggles, edit, and delete capabilities.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    # Quick create modal submission
    create_form = AppUserCreateForm()
    if request.method == 'POST' and 'create_user_submit' in request.POST:
        create_form = AppUserCreateForm(request.POST)
        if create_form.is_valid():
            new_user = create_form.save()
            messages.success(request, f"User '{new_user.name}' ({new_user.email}) registered successfully!")
            return redirect('admin_users')
        else:
            messages.error(request, "Failed to create user. Please check the highlighted errors.")

    # Search & Filter parameters
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()
    sort_order = request.GET.get('sort', 'newest').strip().lower()

    users_queryset = AppUser.objects.all()

    if search_query:
        users_queryset = users_queryset.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile__icontains=search_query)
        )

    if status_filter == 'active':
        users_queryset = users_queryset.filter(is_active=True)
    elif status_filter == 'disabled':
        users_queryset = users_queryset.filter(is_active=False)

    if sort_order == 'oldest':
        users_queryset = users_queryset.order_by('created_at')
    elif sort_order == 'name_asc':
        users_queryset = users_queryset.order_by('name')
    elif sort_order == 'name_desc':
        users_queryset = users_queryset.order_by('-name')
    else:  # default newest
        users_queryset = users_queryset.order_by('-created_at')

    context = get_admin_context(request)
    context['active_nav'] = 'users'
    context['module_title'] = 'Users & Customers Management'
    context['module_icon'] = 'bi-people-fill'
    context['module_description'] = 'Manage registered passenger accounts, edit contact details, toggle activation status, or safely remove user profiles.'

    # Statistics
    context['total_app_users'] = AppUser.objects.count()
    context['active_app_users'] = AppUser.objects.filter(is_active=True).count()
    context['disabled_app_users'] = AppUser.objects.filter(is_active=False).count()
    context['total_custom_admins'] = CustomAdmin.objects.count()
    context['total_system_users'] = User.objects.count()
    context['staff_count'] = User.objects.filter(is_staff=True).count()

    # Listing context
    context['app_users_list'] = users_queryset
    context['filtered_count'] = users_queryset.count()
    context['search_query'] = search_query
    context['status_filter'] = status_filter
    context['sort_order'] = sort_order
    context['create_form'] = create_form
    context['custom_admins_list'] = CustomAdmin.objects.all()[:10]
    context['system_users_list'] = User.objects.all()[:10]

    return render(request, 'core/admin_users.html', context)


@login_required(login_url='admin_login')
def admin_user_create_view(request):
    """
    Dedicated view to register a new App User.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    if request.method == 'POST':
        form = AppUserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"User '{new_user.name}' ({new_user.email}) registered successfully!")
            return redirect('admin_users')
        else:
            messages.error(request, "Failed to create user. Please correct the highlighted errors.")
    else:
        form = AppUserCreateForm()

    context = get_admin_context(request)
    context['active_nav'] = 'users'
    context['form'] = form
    return render(request, 'core/admin_user_create.html', context)


@login_required(login_url='admin_login')
def admin_user_edit_view(request, user_id):
    """
    Edit an existing App User (Name, Email, Mobile, Active Status, Optional Password change).
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    target_user = get_object_or_404(AppUser, pk=user_id)

    if request.method == 'POST':
        form = AppUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{target_user.name}' updated successfully!")
            return redirect('admin_users')
        else:
            messages.error(request, "Failed to update user. Please correct the highlighted errors.")
    else:
        form = AppUserEditForm(instance=target_user)

    context = get_admin_context(request)
    context['active_nav'] = 'users'
    context['target_user'] = target_user
    context['form'] = form
    return render(request, 'core/admin_user_edit.html', context)


@login_required(login_url='admin_login')
def admin_user_delete_view(request, user_id):
    """
    Safely delete an App User from the database.
    Accepts POST or confirmed GET.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    target_user = get_object_or_404(AppUser, pk=user_id)
    user_name = target_user.name
    user_email = target_user.email

    if request.method == 'POST' or request.GET.get('confirm') == 'yes':
        target_user.delete()
        messages.success(request, f"User '{user_name}' ({user_email}) has been permanently deleted.")
        return redirect('admin_users')

    context = get_admin_context(request)
    context['active_nav'] = 'users'
    context['target_user'] = target_user
    return render(request, 'core/admin_user_confirm_delete.html', context)


@login_required(login_url='admin_login')
def admin_user_toggle_status_view(request, user_id):
    """
    Toggle an App User's is_active status (Active <-> Disabled).
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    target_user = get_object_or_404(AppUser, pk=user_id)
    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "activated" if target_user.is_active else "disabled"
    messages.success(request, f"User '{target_user.name}' has been {status_str}.")
    return redirect('admin_users')


@login_required(login_url='admin_login')
def admin_bookings_view(request):
    """
    Placeholder view for future Bookings & Dispatch module.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logout(request)
        messages.error(request, 'Session terminated: Administrator privileges required.')
        return redirect('admin_login')

    context = get_admin_context(request)
    context['active_nav'] = 'bookings'
    context['module_title'] = 'Bookings & Dispatch'
    context['module_icon'] = 'bi-journal-bookmark-fill'
    context['module_description'] = 'Track passenger trip bookings, dispatch cabs, monitor completed rides, and calculate fare payments.'
    context['total_bookings'] = Booking.objects.count()
    context['pending_bookings'] = Booking.objects.filter(status='pending').count()
    context['active_rides'] = Booking.objects.filter(status__in=['ongoing', 'confirmed']).count()
    context['completed_bookings'] = Booking.objects.filter(status='completed').count()
    context['cancelled_bookings'] = Booking.objects.filter(status='cancelled').count()
    context['bookings_list'] = Booking.objects.all()[:10]

    return render(request, 'core/admin_bookings.html', context)


def admin_logout_view(request):
    """
    Admin Logout view using Django authentication.
    Clears the session and redirects to admin login.
    """
    logout(request)
    messages.info(request, 'You have been successfully signed out.')
    return redirect('admin_login')
