from django.db import models


class CustomAdmin(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrator'),
        ('fleet_manager', 'Fleet Manager'),
        ('dispatcher', 'Ride Dispatcher'),
        ('support_lead', 'Customer Support Lead'),
    ]

    full_name = models.CharField(max_length=150)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='fleet_manager')
    password = models.CharField(max_length=255)  # Stored securely hashed with make_password
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'custom_admin_users'
        verbose_name = 'Custom Admin'
        verbose_name_plural = 'Custom Admins'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.username}) - {self.get_role_display()}"


class Driver(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('offline', 'Offline'),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    license_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('auto', 'Auto Rickshaw'),
    ]

    vehicle_number = models.CharField(max_length=20, unique=True)
    model_name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='sedan')
    driver = models.OneToOneField(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.model_name} - {self.vehicle_number}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    booking_id = models.CharField(max_length=20, unique=True)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)
    pickup_location = models.CharField(max_length=255)
    drop_location = models.CharField(max_length=255)
    vehicle_type = models.CharField(max_length=20, default='Sedan')
    fare = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.booking_id} - {self.customer_name}"
