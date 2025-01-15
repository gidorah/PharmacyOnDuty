from datetime import datetime

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from pharmacies.models import City, PharmacyStatus
from pharmacies.utils import (
    add_scraped_data_to_db,
    check_if_scraped_data_old,
    fetch_nearest_pharmacies,
    get_eskisehir_data,
    get_map_points_from_fetched_data,
    get_map_points_from_pharmacies,
    get_nearest_pharmacies_on_duty,
)


def home(request):
    return render(request, "pharmacies/index.html")


def get_pharmacy_points(request):
    user_latitude = float(request.GET.get("lat"))
    user_longitude = float(request.GET.get("lng"))
    city_name = request.GET.get("city", "eskisehir")

    city = City.objects.get(name=city_name)
    city_status = city.get_city_status_for_time() if city else None

    if city_status == PharmacyStatus.OPEN:
        pharmacies = fetch_nearest_pharmacies(
            user_latitude, user_longitude, keyword="pharmacy"
        )
        points = get_map_points_from_fetched_data(pharmacies)
    else:
        data_status = check_if_scraped_data_old("eskisehir")
        if data_status is True:
            eskisehir_data = get_eskisehir_data()
            add_scraped_data_to_db(eskisehir_data)
            eskisehir = City.objects.get(name="eskisehir")
            eskisehir.last_scraped_at = datetime.now()
            eskisehir.save()

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
