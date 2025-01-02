from django.urls import path

from . import views

app_name = "pharmacies"
urlpatterns = [
    path("", views.home, name="home"),
    path("load_map_data", views.load_map_data, name="load_map_data"),
    path("google_maps_proxy", views.google_maps_proxy, name="google_maps_proxy"),
]
