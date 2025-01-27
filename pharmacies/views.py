import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

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


def get_pharmacy_points(request):
    user_latitude = float(request.GET.get("lat"))
    user_longitude = float(request.GET.get("lng"))
    city_name = request.GET.get("city", "eskisehir")

    try:
        city = City.objects.get(name=city_name)
        try:
            city_status = city.get_city_status()
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

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
                try:
                    eskisehir.last_scraped_at = timezone.now()
                    eskisehir.save()
                except Exception as e:
                    return JsonResponse({"error": str(e)}, status=500)

            pharmacies_on_duty = get_nearest_pharmacies_on_duty(
                user_latitude, user_longitude
            )
            points = get_map_points_from_pharmacies(pharmacies_on_duty)

    except City.DoesNotExist:
        return JsonResponse({"error": "City not found."}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    data = {"points": points}
    return JsonResponse(data)


def google_maps_proxy(request):
    endpoint = "https://maps.googleapis.com/maps/api/js"
    params = {
        "key": settings.GOOGLE_MAPS_API_KEY,
        "libraries": "geometry",
        **dict(request.GET),
    }
    response = requests.get(endpoint, params=params, timeout=10)
    return HttpResponse(response.text, content_type="text/javascript")
