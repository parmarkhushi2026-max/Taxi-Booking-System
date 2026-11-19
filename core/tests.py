from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from core.models import CustomAdmin, Driver, Vehicle, Booking


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
        """Submitting email generates a 6-digit random OTP and redirects to verify."""
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
        """Setting new password works after OTP verification."""
        CustomAdmin.objects.create(
            full_name='OTP Reset User',
            username='otp_user',
            email='otpuser@taxi.com',
            phone='9811223344',
            password='oldPasswordHash',
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
