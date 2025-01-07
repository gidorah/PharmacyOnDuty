from pharmacies.models import Pharmacy, City

from datetime import datetime


def get_coordinates_from_google_maps_url(url: str):
    coordinate_string = url.split("=")[-1]
    lat = float(coordinate_string.split(",")[0])
    lng = float(coordinate_string.split(",")[1])
    coordinates = {"lat": lat, "lng": lng}
    return coordinates


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
            "description": pharmacy.address,
        }
        points.append(point)

    return points


def get_nearest_pharmacies_on_duty(lat, lng, radius=1000, limit=5):
    return Pharmacy.objects.filter(
        duty_start__lte=datetime.now(),
        duty_end__gte=datetime.now(),
    ).order_by("location")[:limit]


def check_if_pharmacy_exists(name):
    pharmacy = Pharmacy.objects.filter(name=name).first()
    return True if pharmacy else False


def add_scraped_data_to_db(scraped_data):
    for item in scraped_data:
        if not check_if_pharmacy_exists(item["name"]):
            coordinates = item["coordinates"]
            pharmacy = Pharmacy(
                name=item["name"],
                address=item["address"],
                phone=item["phone"],
                location="POINT({} {})".format(coordinates["lng"], coordinates["lat"]),
                duty_start=item["duty_start"],
                duty_end=item["duty_end"],
                district=item["district"],
                city_id=City.objects.get(name="eskisehir").id,
            )
            pharmacy.save()


if __name__ == "__main__":
    from pharmacies.utils.eskisehireo_scraper import get_eskisehir_data

    eskisehir_data = get_eskisehir_data()
    add_scraped_data_to_db(eskisehir_data)
