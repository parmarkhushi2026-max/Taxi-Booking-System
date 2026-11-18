# Taxi Booking System

A Django-based web application configured with SQLite3 database and custom Admin Portal.

## Project Structure
- `taxi_booking/` - Django configuration and settings
- `core/` - Main application with views, templates, and admin portal
  - `templates/core/base.html` - Base layout with Bootstrap 5
  - `templates/core/admin_login.html` - Manual Admin Login Page (No registration)
  - `templates/core/admin_dashboard.html` - Admin Dashboard
  - `templates/core/index.html` - Homepage
- `manage.py` - Django command line utility
- `requirements.txt` - Project dependencies

## Features
- **Manual Admin Login**: Secure login for staff and superusers (`/admin-login/`).
- **No Public Registration**: Registration is disabled to maintain system exclusivity.
- **Admin Dashboard**: Live metrics, stats cards, and recent booking overviews (`/admin-dashboard/`).
- **SQLite3 Database**: Pre-configured and migrated.

## Getting Started

### 1. Setup Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Run Development Server
```bash
python manage.py runserver
```

### 5. Access the Portals
- **Homepage**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Login**: [http://127.0.0.1:8000/admin-login/](http://127.0.0.1:8000/admin-login/)
- **Admin Dashboard**: [http://127.0.0.1:8000/admin-dashboard/](http://127.0.0.1:8000/admin-dashboard/)
- **Django Backend Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

#### Default Admin Credentials (for local testing):
- **Username**: `admin`
- **Password**: `admin123`
