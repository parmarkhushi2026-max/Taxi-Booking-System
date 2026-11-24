from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('admin-register/', views.admin_register_view, name='admin_register'),
    path('register/', views.admin_register_view, name='register'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('login/', views.admin_login_view, name='login'),
    path('admin-forgot-password/', views.admin_forgot_password_view, name='admin_forgot_password'),
    path('forgot-password/', views.admin_forgot_password_view, name='forgot_password'),
    path('admin-verify-otp/', views.admin_verify_otp_view, name='admin_verify_otp'),
    path('verify-otp/', views.admin_verify_otp_view, name='verify_otp'),
    path('admin-resend-otp/', views.admin_resend_otp_view, name='admin_resend_otp'),
    path('admin-reset-password/', views.admin_reset_password_view, name='admin_reset_password'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-drivers/', views.admin_drivers_view, name='admin_drivers'),
    path('drivers/', views.admin_drivers_view, name='drivers'),
    path('admin-users/', views.admin_users_view, name='admin_users'),
    path('users/', views.admin_users_view, name='users'),
    path('admin-bookings/', views.admin_bookings_view, name='admin_bookings'),
    path('bookings/', views.admin_bookings_view, name='bookings'),
    path('admin-logout/', views.admin_logout_view, name='admin_logout'),
    path('logout/', views.admin_logout_view, name='logout'),
]
