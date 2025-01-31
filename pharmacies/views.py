import traceback

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    fetch_nearest_pharmacies,
    get_city_name_from_location,
    get_map_points_from_fetched_data,
    get_map_points_from_pharmacies,
    get_nearest_pharmacies_on_duty,
    round_lat_lng,
)

TEST_TIME = timezone.now().replace(hour=19, minute=0, second=0, microsecond=0)


def get_pharmacy_points(request):
    try:
        user_latitude = float(request.GET.get("lat"))
        user_longitude = float(request.GET.get("lng"))

        # First round lat and lng to exclude little variations
        lat, lng = round_lat_lng(user_latitude, user_longitude, precision=4)

        # decide the city from the user location
        city_name = get_city_name_from_location(lat, lng)

        city = City.objects.get(name=city_name)

        city_status = city.get_city_status(TEST_TIME)

        if city_status == PharmacyStatus.OPEN:
            pharmacies = fetch_nearest_pharmacies(lat, lng, keyword="pharmacy")
            points = get_map_points_from_fetched_data(pharmacies)
        else:
            pharmacies_on_duty = get_nearest_pharmacies_on_duty(
                lat, lng, city=city_name, time=TEST_TIME
            )

            points = get_map_points_from_pharmacies(pharmacies_on_duty)

        data = {"points": points}
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        return JsonResponse(
            {"error": error_message, "traceback": error_traceback}, status=500
        )
    return JsonResponse(data)


@cache_page(60 * 60)  # cache for 1 hour
def google_maps_proxy(request):
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
