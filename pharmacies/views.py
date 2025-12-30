"""
Views for the Pharmacies application.

This module handles the HTTP requests for pharmacy data, including:
- Serving the main map interface.
- Providing API endpoints for fetching pharmacy data based on location.
- Proxying requests to the Google Maps API.
"""

import json
from datetime import timedelta

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    get_city_name_from_location,
    get_nearest_pharmacies_on_duty,
    get_nearest_pharmacies_open,
    round_lat_lng,
)

TEST_TIME = timezone.now() + timedelta(hours=10)
SHOWN_PHARMACIES = 5


@csrf_exempt
def get_pharmacy_points(request: HttpRequest) -> JsonResponse:
    """
    Handle POST requests to retrieve the nearest pharmacies based on user location.

    This view calculates the user's city from coordinates, checks the city's
    working status (Open/Closed), and returns either open pharmacies or
    pharmacies on duty accordingly.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])  # type: ignore

    try:
        data = json.loads(request.body)
        user_latitude = float(data["lat"])
        user_longitude = float(data["lng"])

        # First round lat and lng to exclude little variations
        lat, lng = round_lat_lng(user_latitude, user_longitude, precision=4)

        # decide the city from the user location
        city_name = get_city_name_from_location(lat, lng)
        city = City.objects.get(name=city_name)

        query_time = TEST_TIME if settings.DEBUG else timezone.now()
        city_status = city.get_city_status(query_time)
        print(f"City status: {city_status}")

        if city_status == PharmacyStatus.OPEN:
            points = get_nearest_pharmacies_open(lat, lng, limit=SHOWN_PHARMACIES)
        else:
            points = get_nearest_pharmacies_on_duty(
                lat, lng, city=city_name, time=query_time, limit=SHOWN_PHARMACIES
            )

        response_data = {"points": points}
        print(f"Pharmacy points: \n {response_data}")
        return JsonResponse(response_data)

    except (ValueError, City.DoesNotExist) as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        import traceback

        traceback.print_exc()
        return JsonResponse({"error": "An internal server error occurred."}, status=500)


def is_allowed_referer(request: HttpRequest) -> bool:
    """
    Check if the request referrer is allowed.

    Used to protect the Google Maps proxy from unauthorized usage.
    """
    referer = request.META.get("HTTP_REFERER", "")
    return any(referer.startswith(allowed) for allowed in settings.ALLOWED_REFERERS)


@cache_page(60 * 60)  # cache for 1 hour
def google_maps_proxy(request: HttpRequest) -> HttpResponse | JsonResponse:
    """
    Proxy request to Google Maps API to hide the API key.

    This view validates the referrer before forwarding the request to Google Maps,
    allowing the frontend to load maps without exposing credentials.
    """
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    if not is_allowed_referer(request):
        return HttpResponse("Forbidden", status=403)

    endpoint = "https://maps.googleapis.com/maps/api/js"
    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
        "libraries": "geometry",
        **dict(request.GET),
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        return HttpResponse(response.text, content_type="text/javascript")
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


def pharmacies_list(request: HttpRequest) -> HttpResponse:
    """Render the main pharmacies page."""
    return render(request, "pharmacies.html")
