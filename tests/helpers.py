import random
from datetime import timedelta
from typing import Any

from django.utils import timezone
from faker import Faker

fake = Faker("tr_TR")

CITY_CENTERS = {
    "istanbul": {"lat": 41.0082, "lng": 28.9784},
    "ankara": {"lat": 39.9334, "lng": 32.8597},
    "eskisehir": {"lat": 39.7667, "lng": 30.5256},
}


def generate_synthetic_pharmacies(count: int = 1000) -> list[dict[str, Any]]:
    """
    Generates a list of synthetic pharmacy data dictionaries.
    Evenly distributes them across the supported cities.
    """
    data = []
    cities = list(CITY_CENTERS.keys())
    now = timezone.now()
    duty_start = now - timedelta(hours=1)
    duty_end = now + timedelta(hours=24)

    for i in range(count):
        city = cities[i % len(cities)]
        center = CITY_CENTERS[city]

        # Randomize location within ~0.1 degree radius (approx 10km)
        lat = center["lat"] + random.uniform(-0.1, 0.1)
        lng = center["lng"] + random.uniform(-0.1, 0.1)

        pharmacy = {
            "name": f"{fake.company()} Eczanesi",
            "address": fake.address(),
            "phone": fake.phone_number()[:16],  # Truncate to fit max_length=16
            "city": city,
            "district": fake.city_suffix(),  # Not accurate district but sufficient for load
            "coordinates": {"lat": lat, "lng": lng},
            "duty_start": duty_start,
            "duty_end": duty_end,
        }
        data.append(pharmacy)

    return data
