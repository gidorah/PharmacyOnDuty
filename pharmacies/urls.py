"""
URL Configuration for the pharmacies application.

Routes:
- get_pharmacy_points: API endpoint to fetch pharmacy data.
- google_maps_proxy: Proxy endpoint for Google Maps API.
- data_health: Read-only per-city data freshness and duty counts.
"""

from django.urls import path

from pharmacies import views

app_name = "pharmacies"
urlpatterns = [
    path("get_pharmacy_points", views.get_pharmacy_points, name="get_pharmacy_points"),
    path("google_maps_proxy", views.google_maps_proxy, name="google_maps_proxy"),
    path("health/data/", views.data_health, name="data_health"),
]
