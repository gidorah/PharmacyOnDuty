import requests

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings

from pharmacies.utils import get_eskisehir_data, get_map_points_from_scraped_data


def home(request):
    return render(request, "pharmacies/index.html")


def load_map_data(request, city):
    scraped_data = get_eskisehir_data()
    points = get_map_points_from_scraped_data(scraped_data)
    data = {"center": {"lat": 39.779154, "lng": 30.519983}, "points": points}
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
