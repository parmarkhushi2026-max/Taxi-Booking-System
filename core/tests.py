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

        # Verify entry exists in custom admin table
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

        # Log in with the registered credentials
        login_res = self.client.post(reverse('admin_login'), {
            'username': 'admin_aman',
            'password': 'Password123!',
        })
        self.assertRedirects(login_res, reverse('admin_dashboard'))

        # Access dashboard
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

    def test_admin_login_page_renders(self):
        """Verify the login page renders with link to registration."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_login.html')
        self.assertContains(response, 'Register Admin')

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
