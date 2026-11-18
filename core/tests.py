from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Driver, Vehicle, Booking


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
        # Create sample data
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

    def test_admin_login_page_renders_without_registration(self):
        """Verify the login page renders and explicitly contains NO registration links."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_login.html')
        content = response.content.decode()
        self.assertIn('Admin Portal', content)
        self.assertIn('Sign In to Admin Panel', content)
        self.assertNotIn('href="/register"', content)
        self.assertNotIn('Sign Up', content)
        self.assertNotIn('Create an account', content)

    def test_admin_login_success_and_redirects_to_dashboard(self):
        """Admin user can log in and gets redirected to the dashboard."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'superadmin',
            'password': 'SecretPassword123'
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_admin_dashboard_loads_after_login(self):
        """Dashboard loads with stats and booking data for logged in admin."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_dashboard.html')
        self.assertContains(response, 'Total Bookings')
        self.assertContains(response, 'Active Rides')
        self.assertContains(response, 'Available Drivers')
        self.assertContains(response, 'TX-TEST')
        self.assertContains(response, 'Test Driver')

    def test_unauthenticated_user_redirected_from_dashboard(self):
        """Unauthenticated user cannot access dashboard and is redirected to login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, f"{reverse('admin_login')}?next={reverse('admin_dashboard')}")

    def test_non_admin_cannot_access_admin_portal(self):
        """Regular non-staff user gets access denied."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'regularuser',
            'password': 'UserPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access denied')

    def test_admin_logout(self):
        """Admin user can log out successfully."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_logout'))
        self.assertRedirects(response, reverse('admin_login'))
