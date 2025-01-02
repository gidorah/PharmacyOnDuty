import requests

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings


def home(request):
    return render(request, "pharmacies/index.html")


def load_map_data(request):
    points = [
        {
            "position": {"lat": 40.73061, "lng": -73.935242},
            "title": "Point 1",
            "description": "This is point 1",
        },
        {
            "position": {"lat": 40.7295, "lng": -73.9965},
            "title": "Point 2",
            "description": "This is point 2",
        },
        {
            "position": {"lat": 40.7128, "lng": -74.0060},
            "title": "Point 3",
            "description": "This is point 3",
        },
    ]

    data = {"center": {"lat": 40.7128, "lng": -74.0060}, "points": points}
    return JsonResponse(data)


def google_maps_proxy(request):
    endpoint = "https://maps.googleapis.com/maps/api/js"
    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
        **dict(request.GET),
    }
    response = requests.get(endpoint, params=params)
    return HttpResponse(response.text, content_type="text/javascript")
