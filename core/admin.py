from django.contrib import admin
from .models import Driver, Vehicle, Booking


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
