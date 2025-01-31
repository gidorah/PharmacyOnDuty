from datetime import datetime, timedelta
from functools import lru_cache

import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone

from pharmacies.models import City, Pharmacy


def get_coordinates_from_google_maps_url(url: str):
    coordinate_string = url.split("=")[-1]
    lat = float(coordinate_string.split(",")[0])
    lng = float(coordinate_string.split(",")[1])
    return {"lat": lat, "lng": lng}


def get_map_points_from_fetched_data(data):
    points = []

    for pharmacy in data:
        point = {
            "position": {
                "lat": pharmacy["geometry"]["location"]["lat"],
                "lng": pharmacy["geometry"]["location"]["lng"],
            },
            "title": pharmacy["name"],
            "description": pharmacy["vicinity"],
            "status": "Açık",
            "address": pharmacy["vicinity"],
            "distance": "-",
        }
        points.append(point)

    return points


def get_map_points_from_pharmacies(pharmacies):
    points = []

    for pharmacy in pharmacies:
        point = {
            "position": {
                "lat": pharmacy.location.coords[1],
                "lng": pharmacy.location.coords[0],
            },
            "title": pharmacy.name,
            "address": pharmacy.address,
            "status": "Nöbetçi",
            "distance": round(pharmacy.distance.m),
        }
        points.append(point)

    return points


def check_if_scraped_data_old(
    city_name: str | None = None, time: datetime | None = None
):
    from pharmacies.models import City, PharmacyStatus

    if city_name is None:
        raise ValueError("City name is required.")

    if time is None:
        time = timezone.now()

    city = City.objects.get(name=city_name)

    if city.get_city_status(timezone.now()) == PharmacyStatus.OPEN:
        return False

    if (
        city.last_scraped_at is None
        or city.get_city_status(city.last_scraped_at) == PharmacyStatus.OPEN
        or city.last_scraped_at.date() < timezone.now().date() - timedelta(hours=6)
    ):
        return True

    return False


def get_nearest_pharmacies_on_duty(
    lat: float | None = None,
    lng: float | None = None,
    city: str | None = None,
    radius: int = 100_000,
    limit: int = 5,
    time: datetime | None = None,
):
    if city is None:
        raise ValueError("City name is required.")

    if lat is None or lng is None:
        raise ValueError("Latitude and longitude are required.")

    if time is None:
        time = timezone.now()

    data_status = check_if_scraped_data_old(city, time=time)
    if data_status is True:
        eskisehir_data = get_eskisehir_data()
        add_scraped_data_to_db(eskisehir_data)
        eskisehir = City.objects.get(name="eskisehir")
        eskisehir.last_scraped_at = time
        eskisehir.save()

    user_location = Point(
        float(lng), float(lat), srid=4326
    )  # Create a point for the given location
    now = timezone.now()

    # Filter pharmacies on duty and within the radius
    pharmacies = (
        Pharmacy.objects.filter(
            duty_start__lte=now,
            duty_end__gte=now,
            location__distance_lte=(user_location, radius),
        )
        .annotate(distance=Distance("location", user_location))  # Calculate distance
        .order_by("distance")  # Order by nearest first
    )

    return pharmacies[:limit]


def check_if_pharmacy_exists(name: str) -> bool:
    pharmacy = Pharmacy.objects.filter(name=name).first()
    return True if pharmacy else False


def add_scraped_data_to_db(scraped_data) -> None:
    for item in scraped_data:
        if not check_if_pharmacy_exists(item["name"]):
            coordinates = item["coordinates"]
            location = Point(float(coordinates["lng"]), float(coordinates["lat"]))
            city: City = City.objects.get(name="eskisehir")

            if not city:
                pass
            pharmacy = Pharmacy(
                name=item["name"],
                address=item["address"],
                phone=item["phone"],
                location=location,
                duty_start=item["duty_start"],
                duty_end=item["duty_end"],
                district=item["district"],
                city_id=city.id,
            )
            pharmacy.save()


@lru_cache(maxsize=1024)
def get_city_name_from_location(lat: float, lng: float) -> str:
    """Retrieve city name using Google Maps Geocoding API"""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={settings.GOOGLE_MAPS_API_KEY}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        raise ValueError("Unable to retrieve city name: status is not OK")

    compound_code: str = data["plus_code"]["compound_code"]

    if compound_code is None:
        raise ValueError("Unable to retrieve city name: compound_code is None")

    # TODO: find and handle cities via DB
    if "İstanbul" in compound_code:
        return "istanbul"

    if "Eskişehir" in compound_code:
        return "eskisehir"

    raise ValueError("Unknown city")


if __name__ == "__main__":
    from pharmacies.utils.eskisehireo_scraper import get_eskisehir_data

    eskisehir_data = get_eskisehir_data()
    add_scraped_data_to_db(eskisehir_data)


def round_lat_lng(lat: float, lng: float, precision: int = 6):
    """Rounds lat and lng to given precision"""

    return round(lat, precision), round(lng, precision)
