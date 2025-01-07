import requests

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    fetch_nearest_pharmacies,
    get_map_points_from_pharmacies,
    get_map_points_from_fetched_data,
    get_nearest_pharmacies_on_duty,
)


def home(request):
    return render(request, "pharmacies/index.html")


def get_pharmacy_points(request):
    user_latitude = request.GET.get("lat")
    user_longitude = request.GET.get("lng")
    city_name = request.GET.get("city", "eskisehir")

    city = City.objects.get(name=city_name)
    city_status = city.get_city_status() if city else None

    if city_status == PharmacyStatus.OPEN:
        pharmacies = fetch_nearest_pharmacies(
            user_latitude, user_longitude, keyword="pharmacy"
        )
        points = get_map_points_from_fetched_data(pharmacies)
    else:
        pharmacies_on_duty = get_nearest_pharmacies_on_duty(
            user_latitude, user_longitude
        )
        points = get_map_points_from_pharmacies(pharmacies_on_duty)

    data = {"points": points}
    return JsonResponse(data)


def google_maps_proxy(request):
    endpoint = "https://maps.googleapis.com/maps/api/js"
    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
        "libraries": "geometry",
        **dict(request.GET),
    }
    response = requests.get(endpoint, params=params)
    return HttpResponse(response.text, content_type="text/javascript")
