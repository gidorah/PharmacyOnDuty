"""
Utility functions for the Pharmacies application.

This module provides helpers for scraping, geospatial calculations,
and interacting with the Google Maps API.
"""

from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Any

import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone

from pharmacies.models import City, Pharmacy
from pharmacies.utils import get_ankara_data, get_eskisehir_data, get_istanbul_data
from pharmacies.utils.pharmacy_fetch import fetch_nearest_pharmacies


def get_nearest_pharmacies_open(
    lat: float, lng: float, limit: int = 5
) -> list[dict[str, Any]]:
    """
    Get pharmacies that are open (standard working hours) near a location.

    Fetches nearest pharmacies from Google Places API, calculates travel distances,
    and sorts them by distance.
    """
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
) -> list[dict[str, Any]]:
    """
    Get nearest duty pharmacies (Nöbetçi Eczane) for a given location and time.

    1. Checks if the city and coordinates are valid.
    2. Filters pharmacies in the database that are on duty at the specified time.
    3. Sorts by distance and calculates travel metrics using Google Maps.
    """
    if city is None:
        raise ValueError("City name is required.")

    if lat is None or lng is None:
        raise ValueError("Latitude and longitude are required.")

    if time is None:
        time = timezone.now()

    city_object = City.objects.get(name=city)

    if city_object is None:
        raise ValueError("City not found")

    user_location = Point(float(lng), float(lat), srid=4326)

    near_pharmacies_on_duty = Pharmacy.objects.filter(city=city_object)
    near_pharmacies_on_duty = near_pharmacies_on_duty.filter(
        duty_start__lte=time, duty_end__gte=time
    )
    near_pharmacies_on_duty = near_pharmacies_on_duty.annotate(
        distance=Distance("location", user_location)
    )
    near_pharmacies_on_duty = near_pharmacies_on_duty.order_by("distance")
    near_pharmacies_on_duty = near_pharmacies_on_duty[: limit * 2]

    if near_pharmacies_on_duty.count() == 0:
        raise ValueError("No pharmacies are on duty at this time.")

    pharmacy_data = get_map_points_from_pharmacies(near_pharmacies_on_duty)
    add_travel_distances_to_pharmacy_data(lat=lat, lng=lng, pharmacy_data=pharmacy_data)
    order_data_by_distance(pharmacy_data)

    return pharmacy_data[:limit]


def get_coordinates_from_google_maps_url(url: str) -> dict[str, float]:
    """
    Extract latitude and longitude from a Google Maps URL.

    Example URL format: ...?q=lat,lng
    """
    coordinate_string = url.split("=")[-1]
    lat = float(coordinate_string.split(",")[0])
    lng = float(coordinate_string.split(",")[1])
    return {"lat": lat, "lng": lng}


def get_map_points_from_fetched_data(data: list[Any]) -> list[dict[str, Any]]:
    """Convert raw Google Places API data into frontend-friendly map points."""
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


def get_map_points_from_pharmacies(pharmacies: Any) -> list[dict[str, Any]]:
    """Convert Pharmacy model instances into frontend-friendly map points."""
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
    """Enum for the status of scraped data (New or Old)."""

    OLD = "old"
    NEW = "new"


def check_scraped_data_age(
    city_name: str | None = None, time: datetime | None = None
) -> ScrapedDataStatus:
    """
    Check if the scraped data for a city is considered 'new' or 'old'.

    Returns 'NEW' if the city is currently 'OPEN' (standard hours).
    Returns 'OLD' if the last scrape was too long ago or during open hours.
    """
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


def get_city_data(city_name: str) -> list[dict[str, Any]]:
    """
    Dispatcher function to call the appropriate scraper for a given city.
    """
    if city_name == "eskisehir":
        return get_eskisehir_data()

    if city_name == "istanbul":
        return get_istanbul_data()

    if city_name == "ankara":
        return get_ankara_data()

    raise ValueError("Unknown city")


def add_scraped_data_to_db(scraped_data: list[dict[str, Any]], city_name: str) -> None:
    """
    Save scraped pharmacy data to the database.

    Updates existing pharmacies or creates new ones. Optimized using bulk operations.
    """
    city: City = City.objects.get(name=city_name)
    if not city:
        raise ValueError("City not found")

    existing_pharmacies = Pharmacy.objects.filter(city=city)
    pharmacy_map = {(p.name, p.phone): p for p in existing_pharmacies}

    pharmacies_to_create = []
    pharmacies_to_update = []

    for item in scraped_data:
        key = (item["name"], item["phone"])
        existing_pharmacy = pharmacy_map.get(key)

        if not existing_pharmacy:
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
                city=city,
            )
            pharmacies_to_create.append(pharmacy)
        else:
            existing_pharmacy.duty_start = item["duty_start"]
            existing_pharmacy.duty_end = item["duty_end"]
            pharmacies_to_update.append(existing_pharmacy)

    Pharmacy.objects.bulk_create(pharmacies_to_create, ignore_conflicts=True)
    Pharmacy.objects.bulk_update(pharmacies_to_update, ["duty_start", "duty_end"])


def _parse_location_identifier(data: dict[str, Any]) -> str:
    """Extract a location identifier (compound code or admin area) from Geocoding results."""
    if data["status"] != "OK" or not data["results"]:
        raise ValueError("Unable to parse_location_identifier: status is not OK")

    compound_code = data.get("plus_code", {}).get("compound_code")
    if compound_code is not None:
        return compound_code  # type: ignore

    for component in data["results"][0]["address_components"]:
        if "administrative_area_level_1" in component["types"]:
            return component["long_name"]  # type: ignore

    raise ValueError("Unable to parse_location_identifier")


@lru_cache(maxsize=1024)
def get_city_name_from_location(lat: float, lng: float) -> str:
    """Retrieve city name using Google Maps Geocoding API"""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={settings.GOOGLE_MAPS_API_KEY}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        raise ValueError("Unable to retrieve city name: status is not OK")

    city_data = _parse_location_identifier(data)
    normalized_data = normalize_string(city_data)

    known_cities = list(City.objects.values_list("name", flat=True))

    for city_slug in known_cities:
        if normalize_string(city_slug) in normalized_data:
            return city_slug

    raise ValueError(f"Unknown city: {city_data}")


@lru_cache(maxsize=1024)
def _get_distance_matrix_data(origins: str, destinations: str) -> dict[str, Any]:
    """Fetch distance matrix data from Google Maps API (Cached)."""
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

    return received_data  # type: ignore


def add_travel_distances_to_pharmacy_data(
    lat: float, lng: float, pharmacy_data: list[dict[str, Any]]
) -> None:
    """
    Get travel distances from origin to multiple destinations
    using Google Maps Distance Matrix API. And add them to data list.
    """

    if not pharmacy_data:
        raise ValueError("Cannot retrieve travel distances. Pharmacy data is empty!")

    destinations_str = "|".join(
        f"{d['position']['lat']},{d['position']['lng']}" for d in pharmacy_data
    )
    origin_str = f"{lat},{lng}"

    received_data = _get_distance_matrix_data(
        origins=origin_str, destinations=destinations_str
    )

    for pharmacy_item, row in zip(pharmacy_data, received_data["rows"][0]["elements"]):
        if row["status"] == "OK":
            pharmacy_item["travel_distance"] = row["distance"]["value"]
            pharmacy_item["travel_duration"] = row["duration"]["value"]
        else:
            pharmacy_item["travel_distance"] = pharmacy_item["distance"]
            pharmacy_item["travel_duration"] = (pharmacy_item["distance"] / 1000) * 60


def order_data_by_distance(pharmacy_data: list[dict[str, Any]]) -> None:
    """Order pharmacy data by travel distance"""
    pharmacy_data.sort(key=lambda x: x["travel_distance"])


def round_lat_lng(lat: float, lng: float, precision: int = 6) -> tuple[float, float]:
    """Rounds lat and lng to given precision"""

    return round(lat, precision), round(lng, precision)


def normalize_string(s: str) -> str:
    """
    Normalize Turkish characters to English equivalents and lowercase the string.

    Example: "ÇANKAYA" -> "cankaya"
    """
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


if __name__ == "__main__":
    from pharmacies.utils.eskisehireo_scraper import get_eskisehir_data

    eskisehir_data = get_eskisehir_data()
    add_scraped_data_to_db(eskisehir_data, city_name="eskisehir")
