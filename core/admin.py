from django.contrib import admin
from .models import CustomAdmin, Driver, Vehicle, Booking


@admin.register(CustomAdmin)
class CustomAdminAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'email', 'phone', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('full_name', 'username', 'email', 'phone')
    readonly_fields = ('created_at', 'last_login')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'license_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'phone', 'license_number')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'model_name', 'vehicle_type', 'driver', 'is_active')
    list_filter = ('vehicle_type', 'is_active')
    search_fields = ('vehicle_number', 'model_name')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'customer_name', 'pickup_location', 'drop_location', 'fare', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('booking_id', 'customer_name', 'customer_phone', 'pickup_location', 'drop_location')
