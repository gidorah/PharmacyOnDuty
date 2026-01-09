import json
import os
import sys
from datetime import timedelta
from typing import Any

import django
import requests
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PharmacyOnDuty.settings")
django.setup()


def record() -> None:
    from django.core.management import call_command

    from pharmacies.models import City, Pharmacy
    from pharmacies.utils.utils import (
        _parse_location_identifier,
        add_scraped_data_to_db,
        normalize_string,
    )

    call_command("seed_cities")

    print("--- Load Fabricated Pharmacies ---")
    try:
        with open("tests/fixtures/fabricated_pharmacies.json") as f:
            fabricated_data = json.load(f)

        city_groups: dict[str, list[dict[str, Any]]] = {}
        for item in fabricated_data:
            c = item["city"]
            if c not in city_groups:
                city_groups[c] = []

            item_copy = item.copy()
            now = timezone.now()
            item_copy["duty_start"] = now - timedelta(hours=1)
            item_copy["duty_end"] = now + timedelta(hours=24)

            city_groups[c].append(item_copy)

        for city_name, items in city_groups.items():
            print(f"Loading {len(items)} fabricated pharmacies for {city_name}...")
            add_scraped_data_to_db(items, city_name)

    except Exception as e:
        print(f"Error loading fabricated pharmacies: {e}")
        return

    print("--- Record API Snapshots ---")
    api_snapshots = {}

    with open("tests/fixtures/location_scenarios.json") as f:
        scenarios = json.load(f)

    record_time = timezone.now()
    cities = ["istanbul", "ankara", "eskisehir"]

    for scen in scenarios:
        lat, lng = scen["latitude"], scen["longitude"]
        desc = scen["description"]
        print(f"Processing {desc} ({lat}, {lng})...")

        geo_key = f"geocode:{lat},{lng}"
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={settings.GOOGLE_MAPS_API_KEY}"

        try:
            geo_resp = requests.get(geo_url, timeout=10)
            geo_data = geo_resp.json()
            api_snapshots[geo_key] = geo_data
        except Exception as e:
            print(f"Geocoding failed for {desc}: {e}")
            continue

        found_city = None
        city_identifier = ""
        if geo_data["status"] == "OK" and geo_data["results"]:
            try:
                city_identifier = _parse_location_identifier(geo_data)
                normalized_id = normalize_string(city_identifier)

                for c in cities:
                    if c in normalized_id:
                        found_city = c
                        break
            except Exception:
                pass

        if found_city:
            try:
                limit = 5
                city_obj = City.objects.get(name=found_city)
                user_loc = Point(float(lng), float(lat), srid=4326)

                candidates = (
                    Pharmacy.objects.filter(
                        city=city_obj,
                        duty_start__lte=record_time,
                        duty_end__gte=record_time,
                    )
                    .annotate(dist=Distance("location", user_loc))
                    .order_by("dist")[: limit * 2]
                )

                if candidates.exists():
                    pharmacy_data = []
                    for p in candidates:
                        pharmacy_data.append(
                            {
                                "position": {
                                    "lat": p.location.coords[1],
                                    "lng": p.location.coords[0],
                                }
                            }
                        )

                    destinations_str = "|".join(
                        f"{d['position']['lat']},{d['position']['lng']}"
                        for d in pharmacy_data
                    )
                    origin_str = f"{lat},{lng}"

                    dm_key = f"distancematrix:{lat},{lng}"
                    dm_url = (
                        "https://maps.googleapis.com/maps/api/distancematrix/json"
                        f"?origins={origin_str}"
                        f"&destinations={destinations_str}"
                        f"&key={settings.GOOGLE_MAPS_API_KEY}"
                    )

                    dm_resp = requests.get(dm_url, timeout=10)
                    dm_data = dm_resp.json()
                    api_snapshots[dm_key] = dm_data
                    print(
                        f"  -> Recorded distance matrix for {len(pharmacy_data)} destinations."
                    )
                else:
                    print(f"  -> No active pharmacies found in {found_city}")

            except Exception as e:
                print(f"Error processing Distance Matrix for {desc}: {e}")
        else:
            print(
                f"  -> City not supported or identified: {city_identifier if city_identifier else 'Unknown'}"
            )

    with open("tests/fixtures/google_api_snapshots.json", "w") as f:
        json.dump(api_snapshots, f, indent=2)
    print("Saved tests/fixtures/google_api_snapshots.json")


if __name__ == "__main__":
    record()
