from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache

import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone

from pharmacies.models import City, Pharmacy
from pharmacies.utils import get_ankara_data, get_eskisehir_data, get_istanbul_data
from pharmacies.utils.pharmacy_fetch import fetch_nearest_pharmacies


def normalize_string(s: str) -> str:
    mapping = {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
    }
    return "".join(mapping.get(c, c) for c in s).lower()


def get_nearest_pharmacies_open(lat: float, lng: float, limit: int = 5) -> list:
    """Get pharmacies that are open"""
    fetched_data = fetch_nearest_pharmacies(lat, lng, limit=limit)
    pharmacy_data = get_map_points_from_fetched_data(fetched_data)
    add_travel_distances_to_pharmacy_data(lat=lat, lng=lng, pharmacy_data=pharmacy_data)
    order_data_by_distance(pharmacy_data)

    return pharmacy_data


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

    city_object = City.objects.get(name=city)

    if city_object is None:
        raise ValueError("City not found")

    user_location = Point(
        float(lng), float(lat), srid=4326
    )  # Create a point for the given location

    # Filter pharmacies on duty and within the radius
    near_pharmacies_on_duty = Pharmacy.objects.filter(city=city_object)
    near_pharmacies_on_duty = near_pharmacies_on_duty.filter(
        duty_start__lte=time, duty_end__gte=time
    )
    near_pharmacies_on_duty = near_pharmacies_on_duty.annotate(
        distance=Distance("location", user_location)
    )
    near_pharmacies_on_duty = near_pharmacies_on_duty.order_by(
        "distance"
    )  # Order by nearest first
    near_pharmacies_on_duty = near_pharmacies_on_duty[
        : limit * 2
    ]  # Limit to twice the limit to account for travel distances

    if near_pharmacies_on_duty.count() == 0:
        raise ValueError("No pharmacies are on duty at this time.")

    # Get pharmacies with travel distances.
    pharmacy_data = get_map_points_from_pharmacies(near_pharmacies_on_duty)
    add_travel_distances_to_pharmacy_data(lat=lat, lng=lng, pharmacy_data=pharmacy_data)
    order_data_by_distance(pharmacy_data)

    return pharmacy_data[:limit]


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


class ScrapedDataStatus(Enum):
    OLD = "old"
    NEW = "new"


def check_scraped_data_age(
    city_name: str | None = None, time: datetime | None = None
) -> ScrapedDataStatus:
    from pharmacies.models import City, PharmacyStatus

    if city_name is None:
        raise ValueError("City name is required.")

    if time is None:
        time = timezone.now()

    city = City.objects.get(name=city_name)

    if city.get_city_status(time) == PharmacyStatus.OPEN:
        return ScrapedDataStatus.NEW

    if (
        city.last_scraped_at is None
        or city.get_city_status(city.last_scraped_at) == PharmacyStatus.OPEN
        or city.last_scraped_at.date() < time.date() - timedelta(hours=1)
    ):
        return ScrapedDataStatus.OLD

    return ScrapedDataStatus.OLD


def get_city_data(city_name: str):
    if city_name == "eskisehir":
        return get_eskisehir_data()

    if city_name == "istanbul":
        return get_istanbul_data()

    if city_name == "ankara":
        return get_ankara_data()

    raise ValueError("Unknown city")


def check_if_pharmacy_exists(name: str, phone: str) -> bool:
    pharmacy = Pharmacy.objects.filter(name=name).filter(phone=phone).first()
    return True if pharmacy else False


def add_scraped_data_to_db(scraped_data, city_name: str) -> None:
    city: City = City.objects.get(name=city_name)
    if not city:
        raise ValueError("City not found")

    pharmacies_to_create = []
    pharmacies_to_update = []

    for item in scraped_data:
        if not check_if_pharmacy_exists(item["name"], item["phone"]):
            coordinates = item["coordinates"]
            location = Point(float(coordinates["lng"]), float(coordinates["lat"]))

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
            pharmacies_to_create.append(pharmacy)
        else:
            pharmacy = (
                Pharmacy.objects.filter(name=item["name"])
                .filter(phone=item["phone"])
                .first()
            )
            pharmacy.duty_start = item["duty_start"]
            pharmacy.duty_end = item["duty_end"]
            pharmacies_to_update.append(pharmacy)

    Pharmacy.objects.bulk_create(pharmacies_to_create, ignore_conflicts=True)
    Pharmacy.objects.bulk_update(pharmacies_to_update, ["duty_start", "duty_end"])


def extract_city_name_from_google_maps_response(data):
    if data["status"] != "OK" or not data["results"]:
        raise ValueError("Unable to retrieve city name: status is not OK")

    compound_code = data["plus_code"].get("compound_code")

    if compound_code is not None:
        return compound_code

    for component in data["results"][0]["address_components"]:
        if "administrative_area_level_1" in component["types"]:
            return component["long_name"]

    raise ValueError("Unknown city")


@lru_cache(maxsize=1024)
def get_city_name_from_location(lat: float, lng: float) -> str:
    """Retrieve city name using Google Maps Geocoding API"""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={settings.GOOGLE_MAPS_API_KEY}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        raise ValueError("Unable to retrieve city name: status is not OK")

    city_data = extract_city_name_from_google_maps_response(data)
    normalized_city_data = normalize_string(city_data)

    # Find matching city from DB
    cities = list(City.objects.all())
    # Sort by length descending to avoid partial matches (e.g. "Van" in "Tatvan")
    cities.sort(key=lambda x: len(x.name), reverse=True)

    for city in cities:
        # Check if normalized city name from DB is in normalized city data from Google
        normalized_city_name = normalize_string(city.name)
        if normalized_city_name in normalized_city_data:
            return normalized_city_name

    raise ValueError("Unknown city")


@lru_cache(maxsize=1024)
def _get_distance_matrix_data(origins: str, destinations: str):
    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={origins}"
        f"&destinations={destinations}"
        f"&key={settings.GOOGLE_MAPS_API_KEY}"
    )

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    received_data = response.json()

    if received_data["status"] != "OK":
        raise ValueError(f"Distance Matrix API error: {received_data['status']}")

    return received_data


def add_travel_distances_to_pharmacy_data(
    lat: float, lng: float, pharmacy_data: list
) -> None:
    """
    Get travel distances from origin to multiple destinations
    using Google Maps Distance Matrix API. And add them to data list.
    """

    if not pharmacy_data:
        raise ValueError("Cannot retrieve travel distances. Pharmacy data is empty!")

    # Format destinations for the API request
    destinations_str = "|".join(
        f"{d['position']['lat']},{d['position']['lng']}" for d in pharmacy_data
    )
    origin_str = f"{lat},{lng}"

    received_data = _get_distance_matrix_data(
        origins=origin_str, destinations=destinations_str
    )

    # Add travel information to each destination
    for i, row in enumerate(received_data["rows"][0]["elements"]):
        if row["status"] == "OK":
            pharmacy_data[i]["travel_distance"] = row["distance"]["value"]
            pharmacy_data[i]["travel_duration"] = row["duration"]["value"]
        else:
            pharmacy_data[i]["travel_distance"] = pharmacy_data[i]["distance"]
            pharmacy_data[i]["travel_duration"] = (
                pharmacy_data[i]["distance"] / 1000
            ) * 60  # Convert distance to seconds. A very rough estimate


def order_data_by_distance(pharmacy_data: list) -> None:
    """Order pharmacy data by travel distance"""
    pharmacy_data.sort(key=lambda x: x["travel_distance"])


if __name__ == "__main__":
    from pharmacies.utils.eskisehireo_scraper import get_eskisehir_data

    eskisehir_data = get_eskisehir_data()
    add_scraped_data_to_db(eskisehir_data, city_name="eskisehir")


def round_lat_lng(lat: float, lng: float, precision: int = 6):
    """Rounds lat and lng to given precision"""

    return round(lat, precision), round(lng, precision)
