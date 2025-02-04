from datetime import timedelta

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    get_city_name_from_location,
    get_nearest_pharmacies_on_duty,
    get_nearest_pharmacies_open,
    round_lat_lng,
)

TEST_TIME = timezone.now()
SHOWN_PHARMACIES = 5


def get_pharmacy_points(request):
    user_latitude = float(request.GET.get("lat"))
    user_longitude = float(request.GET.get("lng"))

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

    data = {"points": points}
    print(f"Pharmacy points: \n {data}")
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
