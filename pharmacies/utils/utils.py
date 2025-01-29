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
            "status": "open",
            "address": pharmacy["formatted_address"],
            "distance": pharmacy["distance"]["text"],
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
            "status": "on duty",
            "distance": pharmacy.distance.m,
        }
        points.append(point)

    return points


def check_if_scraped_data_old(city_name):
    from datetime import timedelta

    from pharmacies.models import City, PharmacyStatus

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


def get_nearest_pharmacies_on_duty(lat, lng, radius=1000000, limit=5):
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


if __name__ == "__main__":
    from pharmacies.utils.eskisehireo_scraper import get_eskisehir_data

    eskisehir_data = get_eskisehir_data()
    add_scraped_data_to_db(eskisehir_data)
