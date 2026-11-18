from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


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

    def test_admin_login_page_renders_without_registration(self):
        """Verify the login page renders and explicitly contains NO registration links."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin_login.html')
        content = response.content.decode()
        self.assertIn('Admin Portal', content)
        self.assertIn('Sign In to Admin Panel', content)
        # Ensure there is NO registration / register / sign up link
        self.assertNotIn('href="/register"', content)
        self.assertNotIn('Sign Up', content)
        self.assertNotIn('Create an account', content)

    def test_admin_login_success(self):
        """Admin user can log in and gets redirected to dashboard."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'superadmin',
            'password': 'SecretPassword123'
        })
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_non_admin_cannot_access_admin_portal(self):
        """Regular non-staff user gets access denied."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'regularuser',
            'password': 'UserPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access denied')

    def test_invalid_credentials(self):
        """Wrong password shows error message."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'superadmin',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct')

    def test_admin_logout(self):
        """Admin user can log out successfully."""
        self.client.login(username='superadmin', password='SecretPassword123')
        response = self.client.get(reverse('admin_logout'))
        self.assertRedirects(response, reverse('admin_login'))
