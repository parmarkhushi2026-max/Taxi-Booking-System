from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.db import IntegrityError, transaction
from core.models import User as AppUser, CustomAdmin, Driver, Vehicle, Booking


class AdminLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='superadmin',
            email='admin@taxi.com',
            password='SecretPassword123'
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='user@taxi.com',
            password='UserPassword123'
        )
        self.driver = Driver.objects.create(
            name='Test Driver',
            phone='9999988888',
            license_number='DLTEST123',
            status='available'
        )
        self.booking = Booking.objects.create(
            booking_id='TX-TEST',
            customer_name='Test Customer',
            customer_phone='9888877777',
            pickup_location='Point A',
            drop_location='Point B',
            vehicle_type='Sedan',
            fare=500.00,
            status='completed'
        )

    def test_homepage_renders_real_web_content(self):
        """Verify the homepage renders like a real taxi booking website."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/index.html')
        content = response.content.decode()
        self.assertIn('Book a Cab', content)
        self.assertIn('Our Modern Fleet', content)

    def test_book_ride_from_homepage(self):
        """Passenger can book a ride from the homepage and it saves to DB."""
        response = self.client.post(reverse('index'), {
            'customer_name': 'Vikas Patel',
            'customer_phone': '9876500000',
            'pickup_location': 'Airport Terminal 3',
            'drop_location': 'Connaught Place',
            'vehicle_type': 'Sedan',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Booking.objects.filter(customer_name='Vikas Patel').exists())

    def test_admin_register_page_renders(self):
        """Verify the admin registration page renders properly."""
        response = self.client.get(reverse('admin_register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_register.html')
        self.assertContains(response, 'Admin Registration')
        self.assertContains(response, 'custom_admin_users')

    def test_admin_registration_persists_in_custom_admin_table(self):
        """Verify submitting registration stores data in the custom admin table."""
        response = self.client.post(reverse('admin_register'), {
            'full_name': 'Rajendra Singh',
            'username': 'admin_rajendra',
            'email': 'rajendra@taxi.com',
            'phone': '9812345678',
            'role': 'fleet_manager',
            'password': 'SecurePassword@123',
            'confirm_password': 'SecurePassword@123',
        })
        self.assertRedirects(response, reverse('admin_login'))

        custom_admin = CustomAdmin.objects.filter(username='admin_rajendra').first()
        self.assertIsNotNone(custom_admin)
        self.assertEqual(custom_admin.full_name, 'Rajendra Singh')
        self.assertEqual(custom_admin.email, 'rajendra@taxi.com')
        self.assertEqual(custom_admin.role, 'fleet_manager')
        self.assertTrue(check_password('SecurePassword@123', custom_admin.password))

    def test_custom_admin_can_login_and_access_dashboard(self):
        """An admin registered in custom admin table can log in successfully."""
        self.client.post(reverse('admin_register'), {
            'full_name': 'Aman Verma',
            'username': 'admin_aman',
            'email': 'aman@taxi.com',
            'phone': '9899911122',
            'role': 'dispatcher',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
        })

        login_res = self.client.post(reverse('admin_login'), {
            'username': 'admin_aman',
            'password': 'Password123!',
        })
        self.assertRedirects(login_res, reverse('admin_dashboard'))

        dash_res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, 'Aman Verma')

    def test_admin_registration_password_mismatch(self):
        """Registration fails if passwords do not match."""
        response = self.client.post(reverse('admin_register'), {
            'full_name': 'Fail Test',
            'username': 'fail_admin',
            'email': 'fail@taxi.com',
            'phone': '9800000000',
            'role': 'fleet_manager',
            'password': 'Password1',
            'confirm_password': 'Password2',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')
        self.assertFalse(CustomAdmin.objects.filter(username='fail_admin').exists())

    def test_admin_forgot_password_generates_random_otp(self):
        """Submitting email generates a 6-digit random OTP, sends console email, and redirects to verify."""
        response = self.client.post(reverse('admin_forgot_password'), {
            'email': 'admin@taxi.com',
        })
        self.assertRedirects(response, reverse('admin_verify_otp'))

        # Check that OTP is a 6-digit numeric string generated via random library
        session = self.client.session
        otp = session.get('reset_otp')
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertTrue(100000 <= int(otp) <= 999999)

        # Verify console-based email dispatch
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(otp, mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['admin@taxi.com'])
        self.assertIn("Password Reset OTP", mail.outbox[0].subject)

    def test_admin_verify_otp_valid_and_invalid(self):
        """Test verifying matching and non-matching OTP."""
        # Step 1: Initiate forgot password to set session OTP
        self.client.post(reverse('admin_forgot_password'), {
            'email': 'admin@taxi.com',
        })
        valid_otp = self.client.session.get('reset_otp')

        # Step 2: Try invalid OTP
        invalid_res = self.client.post(reverse('admin_verify_otp'), {
            'otp': '000000' if valid_otp != '000000' else '111111',
        })
        self.assertEqual(invalid_res.status_code, 200)
        self.assertContains(invalid_res, 'Invalid OTP code')

        # Step 3: Try valid OTP
        valid_res = self.client.post(reverse('admin_verify_otp'), {
            'otp': valid_otp,
        })
        self.assertRedirects(valid_res, reverse('admin_reset_password'))
        self.assertTrue(self.client.session.get('otp_verified'))

    def test_admin_resend_otp_generates_fresh_random_otp(self):
        """Resending OTP creates a fresh 6-digit random code."""
        self.client.post(reverse('admin_forgot_password'), {
            'email': 'admin@taxi.com',
        })
        first_otp = self.client.session.get('reset_otp')

        # Request resend
        resend_res = self.client.get(reverse('admin_resend_otp'))
        self.assertRedirects(resend_res, reverse('admin_verify_otp'))

        new_otp = self.client.session.get('reset_otp')
        self.assertEqual(len(new_otp), 6)
        self.assertTrue(new_otp.isdigit())

    def test_admin_reset_password_after_otp_verification(self):
        """Setting new password works after OTP verification and allows immediate login."""
        CustomAdmin.objects.create(
            full_name='OTP Reset User',
            username='otp_user',
            email='otpuser@taxi.com',
            phone='9811223344',
            password=make_password('oldPasswordHash'),
        )

        # Initiate forgot password
        self.client.post(reverse('admin_forgot_password'), {
            'email': 'otpuser@taxi.com',
        })
        otp = self.client.session.get('reset_otp')

        # Verify OTP
        self.client.post(reverse('admin_verify_otp'), {'otp': otp})

        # Set new password
        reset_res = self.client.post(reverse('admin_reset_password'), {
            'new_password': 'UpdatedPassword@2026',
            'confirm_password': 'UpdatedPassword@2026',
        })
        self.assertRedirects(reset_res, reverse('admin_login'))

        custom_admin = CustomAdmin.objects.get(email='otpuser@taxi.com')
        self.assertTrue(check_password('UpdatedPassword@2026', custom_admin.password))

        # Test logging in with the newly reset password
        login_res = self.client.post(reverse('admin_login'), {
            'username': 'otp_user',
            'password': 'UpdatedPassword@2026',
        })
        self.assertRedirects(login_res, reverse('admin_dashboard'))

    def test_admin_reset_password_blocked_without_otp_verification(self):
        """Direct access to reset password without verifying OTP is blocked."""
        response = self.client.get(reverse('admin_reset_password'))
        self.assertRedirects(response, reverse('admin_forgot_password'))

    def test_admin_reset_password_validation_errors(self):
        """Password reset rejects mismatch and passwords under 6 characters."""
        CustomAdmin.objects.create(
            full_name='Test Admin',
            username='test_admin',
            email='testadmin@taxi.com',
            password=make_password('pass123'),
        )
        # Setup session as verified
        session = self.client.session
        session['reset_email'] = 'testadmin@taxi.com'
        session['otp_verified'] = True
        session.save()

        # Mismatch
        res_mismatch = self.client.post(reverse('admin_reset_password'), {
            'new_password': 'Password123',
            'confirm_password': 'PasswordDifferent',
        })
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertContains(res_mismatch, "Passwords do not match")

        # Short password (< 6 chars)
        res_short = self.client.post(reverse('admin_reset_password'), {
            'new_password': '123',
            'confirm_password': '123',
        })
        self.assertEqual(res_short.status_code, 200)
        self.assertContains(res_short, "Password must be at least 6 characters long")

    def test_admin_login_page_renders(self):
        """Verify the login page renders with link to registration and forgot password."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_login.html')
        self.assertContains(response, 'Register Admin')
        self.assertContains(response, 'Forgot Password?')

    def test_admin_login_success_and_redirects_to_dashboard(self):
        """Admin user can log in and gets redirected to the dashboard."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'superadmin',
            'password': 'SecretPassword123'
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_unauthenticated_user_redirected_from_dashboard(self):
        """Unauthenticated user cannot access dashboard and is redirected to login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, f"{reverse('admin_login')}?next={reverse('admin_dashboard')}")

    def test_admin_logout(self):
        """Admin user can log out successfully."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_logout'))
        self.assertRedirects(response, reverse('admin_login'))

    def test_admin_dashboard_displays_admin_name_and_profile_image(self):
        """Dashboard displays the authenticated admin full name and profile image."""
        CustomAdmin.objects.create(
            full_name='Vikramaditya Sharma',
            username='vikram_admin',
            email='vikram@taxibooking.com',
            phone='9812345678',
            role='fleet_manager',
            password=make_password('Pass@1234'),
        )
        self.client.post(reverse('admin_login'), {
            'username': 'vikram_admin',
            'password': 'Pass@1234'
        })
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vikramaditya Sharma')
        self.assertContains(response, 'admin-hero-avatar')
        self.assertContains(response, 'admin-avatar-img')
        self.assertContains(response, 'Fleet Manager')

    def test_unauthenticated_user_redirected_from_placeholder_modules(self):
        """Unauthenticated requests to placeholder modules redirect to login."""
        for route in ['admin_drivers', 'admin_users', 'admin_bookings']:
            res = self.client.get(reverse(route))
            self.assertRedirects(res, f"{reverse('admin_login')}?next={reverse(route)}")

    def test_admin_drivers_placeholder_view(self):
        """Authenticated admin can view the Drivers placeholder page."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_drivers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Drivers Management')
        self.assertContains(response, 'Registered Drivers List')
        self.assertContains(response, 'Test Driver')

    def test_admin_users_placeholder_view(self):
        """Authenticated admin can view the Users placeholder page."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Users & Accounts')
        self.assertContains(response, 'Registered Custom Administrators')

    def test_admin_bookings_placeholder_view(self):
        """Authenticated admin can view the Bookings placeholder page."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bookings & Dispatch')
        self.assertContains(response, 'Recent Passenger Bookings')
        self.assertContains(response, 'Test Customer')

    def test_user_model_creation_and_fields(self):
        """Create a User instance with name, email, mobile, password."""
        user = AppUser.objects.create(
            name='Aarav Mehta',
            email='aarav@example.com',
            mobile='9876543210',
            password=make_password('UserSecurePass!'),
        )
        self.assertEqual(user.name, 'Aarav Mehta')
        self.assertEqual(user.email, 'aarav@example.com')
        self.assertEqual(user.mobile, '9876543210')
        self.assertTrue(user.is_active)
        self.assertEqual(str(user), 'Aarav Mehta (aarav@example.com)')
        self.assertTrue(user.check_password('UserSecurePass!'))
        self.assertFalse(user.check_password('WrongPass'))

    def test_user_password_hashing_helpers(self):
        """User model set_password and check_password helper methods work."""
        user = AppUser(name='Priya Sharma', email='priya@example.com', mobile='9123456789')
        user.set_password('MySecret@2026')
        user.save()
        self.assertTrue(user.check_password('MySecret@2026'))
        self.assertFalse(user.check_password('Incorrect'))

    def test_user_model_unique_constraints(self):
        """User email and mobile must be unique."""
        AppUser.objects.create(
            name='First User',
            email='unique@example.com',
            mobile='9991112222',
            password=make_password('pass1'),
        )
        # Duplicate email
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                AppUser.objects.create(
                    name='Second User',
                    email='unique@example.com',
                    mobile='9993334444',
                    password=make_password('pass2'),
                )
        # Duplicate mobile
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                AppUser.objects.create(
                    name='Third User',
                    email='another@example.com',
                    mobile='9991112222',
                    password=make_password('pass3'),
                )

    def test_admin_users_view_displays_registered_app_users(self):
        """Users dashboard module displays registered AppUser records."""
        AppUser.objects.create(
            name='Kavita Joshi',
            email='kavita@taxiapp.com',
            mobile='9822334455',
            password=make_password('KavitaPass123'),
        )
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kavita Joshi')
        self.assertContains(response, 'kavita@taxiapp.com')
        self.assertContains(response, '9822334455')

    def test_admin_user_listing_has_edit_and_delete_options(self):
        """User listing page provides edit and delete action options for each user."""
        user = AppUser.objects.create(
            name='Rahul Verma',
            email='rahul@taxiapp.com',
            mobile='9871122334',
            password=make_password('SecurePass123'),
        )
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        edit_url = reverse('admin_user_edit', args=[user.id])
        delete_url = reverse('admin_user_delete', args=[user.id])
        self.assertContains(response, edit_url)
        self.assertContains(response, delete_url)
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Delete')

    def test_admin_user_edit_view_get_and_post(self):
        """Admin can load edit page and update user details including name, mobile, and password."""
        user = AppUser.objects.create(
            name='Sneha Kapoor',
            email='sneha@taxiapp.com',
            mobile='9811122334',
            password=make_password('OldPassword123'),
        )
        self.client.login(username='superadmin', password='SecretPassword123')

        # GET edit view
        edit_url = reverse('admin_user_edit', args=[user.id])
        get_response = self.client.get(edit_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'Sneha Kapoor')
        self.assertContains(get_response, 'sneha@taxiapp.com')

        # POST update
        post_response = self.client.post(edit_url, {
            'name': 'Sneha Malhotra',
            'email': 'sneha.m@taxiapp.com',
            'mobile': '9899988877',
            'is_active': True,
            'new_password': 'NewPassword456',
        }, follow=True)
        self.assertEqual(post_response.status_code, 200)

        user.refresh_from_db()
        self.assertEqual(user.name, 'Sneha Malhotra')
        self.assertEqual(user.email, 'sneha.m@taxiapp.com')
        self.assertEqual(user.mobile, '9899988877')
        self.assertTrue(user.check_password('NewPassword456'))

    def test_admin_user_delete_view_post(self):
        """Admin can permanently delete an AppUser record."""
        user = AppUser.objects.create(
            name='Temporary User',
            email='temp@taxiapp.com',
            mobile='9000000001',
            password=make_password('Pass123'),
        )
        user_id = user.id
        self.client.login(username='superadmin', password='SecretPassword123')

        delete_url = reverse('admin_user_delete', args=[user_id])
        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AppUser.objects.filter(pk=user_id).exists())

    def test_admin_user_toggle_status_view(self):
        """Admin can toggle is_active status of a user."""
        user = AppUser.objects.create(
            name='Toggle User',
            email='toggle@taxiapp.com',
            mobile='9000000002',
            password=make_password('Pass123'),
            is_active=True,
        )
        self.client.login(username='superadmin', password='SecretPassword123')

        toggle_url = reverse('admin_user_toggle_status', args=[user.id])
        response = self.client.get(toggle_url, follow=True)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        # Toggle back to active
        response = self.client.get(toggle_url, follow=True)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_admin_user_search_and_filter(self):
        """Search query filters users by name, email, or mobile."""
        AppUser.objects.create(name='Mohit Sharma', email='mohit@search.com', mobile='9111122223', password='pass')
        AppUser.objects.create(name='Geeta Patel', email='geeta@search.com', mobile='9333344445', password='pass')

        self.client.login(username='superadmin', password='SecretPassword123')

        # Search for Mohit
        response = self.client.get(reverse('admin_users') + '?q=mohit')
        self.assertContains(response, 'Mohit Sharma')
        self.assertNotContains(response, 'Geeta Patel')

        # Search by phone number
        response = self.client.get(reverse('admin_users') + '?q=9333344445')
        self.assertContains(response, 'Geeta Patel')
        self.assertNotContains(response, 'Mohit Sharma')

    def test_admin_user_detailed_profile_view(self):
        """Admin can view detailed profile of an individual user including metadata and ride history."""
        user = AppUser.objects.create(
            name='Divya Singhania',
            email='divya.s@taxiapp.com',
            mobile='9887766554',
            password=make_password('DivyaPass123!'),
        )
        # Create an associated booking
        Booking.objects.create(
            booking_id='TX-9901',
            customer_name='Divya Singhania',
            customer_phone='9887766554',
            pickup_location='Airport Terminal 2',
            drop_location='Tech Park Gate 1',
            vehicle_type='Sedan',
            fare=650.00,
            status='completed',
        )

        self.client.login(username='superadmin', password='SecretPassword123')
        detail_url = reverse('admin_user_detail', args=[user.id])
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Divya Singhania')
        self.assertContains(response, 'divya.s@taxiapp.com')
        self.assertContains(response, '9887766554')
        self.assertContains(response, 'TX-9901')
        self.assertContains(response, 'Airport Terminal 2')
        self.assertContains(response, 'Tech Park Gate 1')
        self.assertContains(response, 'Detailed User Profile')

    def test_user_search_by_name_and_by_email(self):
        """Implement user search by name or email address."""
        u1 = AppUser.objects.create(name='Ananya Roy', email='ananya.roy@taxiapp.com', mobile='9111000001', password='pass')
        u2 = AppUser.objects.create(name='Suresh Nair', email='suresh.nair@taxiapp.com', mobile='9111000002', password='pass')

        self.client.login(username='superadmin', password='SecretPassword123')

        # 1. Search by Name
        resp_name = self.client.get(reverse('admin_users') + '?q=Ananya')
        self.assertContains(resp_name, 'Ananya Roy')
        self.assertNotContains(resp_name, 'Suresh Nair')

        # 2. Search by Email
        resp_email = self.client.get(reverse('admin_users') + '?q=suresh.nair@taxiapp.com')
        self.assertContains(resp_email, 'Suresh Nair')
        self.assertNotContains(resp_email, 'Ananya Roy')

    def test_bootstrap_table_user_list_display(self):
        """User list displays via Bootstrap table styling with action options."""
        user = AppUser.objects.create(
            name='Kunal Desai',
            email='kunal@taxiapp.com',
            mobile='9222333444',
            password=make_password('Pass123'),
        )
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_users'))

        self.assertEqual(response.status_code, 200)
        # Check Bootstrap table elements
        self.assertContains(response, 'table-dark')
        self.assertContains(response, 'table-hover')
        self.assertContains(response, 'table-striped')
        self.assertContains(response, 'table-responsive')
        # Check action buttons
        self.assertContains(response, 'View')
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Delete')
        self.assertContains(response, reverse('admin_user_detail', args=[user.id]))
