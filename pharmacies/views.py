"""
Views for the Pharmacies application.

This module handles the HTTP requests for pharmacy data, including:
- Serving the main map interface.
- Providing API endpoints for fetching pharmacy data based on location.
- Proxying requests to the Google Maps API.
"""

from datetime import timedelta
from json import JSONDecodeError, loads

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    get_city_name_from_location,
    get_nearest_pharmacies_on_duty,
    get_nearest_pharmacies_open,
    round_lat_lng,
)

TEST_TIME = timezone.now() + timedelta(hours=10)
SHOWN_PHARMACIES = 5


@ratelimit(key="ip", rate="30/m", method="POST", block=True)
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
        data = loads(request.body)
    except JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    missing_fields = sorted({"lat", "lng"} - data.keys())
    if missing_fields:
        fields = ", ".join(missing_fields)
        return JsonResponse(
            {"error": f"Missing required fields: {fields}."}, status=400
        )

    try:
        user_latitude = float(data["lat"])
        user_longitude = float(data["lng"])
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid coordinates."}, status=400)

    if not (-90 <= user_latitude <= 90) or not (-180 <= user_longitude <= 180):
        return JsonResponse({"error": "Invalid coordinates."}, status=400)

    try:
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

    except City.DoesNotExist:
        return JsonResponse(
            {"error": "No city found for the provided location."}, status=400
        )
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
    # The "marker" library is required for AdvancedMarkerElement and the
    # "routes" library provides DirectionsService / DirectionsRenderer via
    # google.maps.importLibrary("routes"), which is the non-deprecated
    # modular access pattern for those classes.
    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
        "libraries": "marker,routes,geometry",
        **dict(request.GET),
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        return HttpResponse(response.text, content_type="text/javascript")
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


def pharmacies_list(request: HttpRequest) -> HttpResponse:
    """Render the main pharmacies page."""
    return render(
        request,
        "pharmacies.html",
        {"google_maps_map_id": settings.GOOGLE_MAPS_MAP_ID},
    )


def ratelimit_error(
    request: HttpRequest, exception: Exception | None = None
) -> JsonResponse:
    """Return a JSON 429 response when the rate limit is exceeded."""
    response = JsonResponse(
        {"error": "Too many requests. Please slow down."}, status=429
    )
    response["Retry-After"] = "60"
    return response
