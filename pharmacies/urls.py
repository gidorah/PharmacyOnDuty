from django.urls import path

from pharmacies import views

app_name = "pharmacies"
urlpatterns = [
    path("get_pharmacy_points", views.get_pharmacy_points, name="get_pharmacy_points"),
    path("google_maps_proxy", views.google_maps_proxy, name="google_maps_proxy"),
]
