# Taxi Booking System

A Django-based web application configured with SQLite3 database.

## Project Structure
- `taxi_booking/` - Django configuration and settings
- `manage.py` - Django command line utility
- `requirements.txt` - Project dependencies

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

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
