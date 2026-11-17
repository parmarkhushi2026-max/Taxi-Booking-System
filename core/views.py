from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("<h1>Welcome to Taxi Booking System</h1><p>Core app is configured and ready.</p>")
