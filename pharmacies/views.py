import requests

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    fetch_nearest_pharmacies,
    get_map_points_from_pharmacies,
    get_nearest_pharmacies_on_duty,
)


def home(request):
    return render(request, "pharmacies/index.html")


def load_map_data(request, city_name):
    city = City.objects.get(name=city_name)
    city_status = city.get_city_status() if city else None

    if city_status == PharmacyStatus.OPEN:
        data = fetch_nearest_pharmacies(39.779154, 30.519984)

        points = []

        for pharmacy in data:
            point = {
                "position": {
                    "lat": pharmacy["geometry"]["location"]["lat"],
                    "lng": pharmacy["geometry"]["location"]["lng"],
                },
                "title": pharmacy["name"],
                "description": pharmacy["vicinity"],
            }
            points.append(point)
    else:
        pharmacies_on_duty = get_nearest_pharmacies_on_duty(39.779154, 30.519984)
        points = get_map_points_from_pharmacies(pharmacies_on_duty)

    data = {"center": {"lat": 39.779154, "lng": 30.519984}, "points": points}
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
