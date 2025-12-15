from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


def _get_district_from_name(pharmacy_name: str) -> str:
    return pharmacy_name.split(" ")[-1]


def _get_duty_dates(operation_times: str) -> tuple[datetime, datetime]:
    parts = operation_times.split(" ")
    start_date = datetime.strptime(parts[0] + " " + parts[1], "%d.%m.%Y %H:%M")
    end_date = datetime.strptime(parts[3] + " " + parts[4], "%d.%m.%Y %H:%M")
    return start_date, end_date


def get_eskisehir_data() -> list[dict[str, Any]]:
    from pharmacies.utils import get_coordinates_from_google_maps_url

    url = "https://www.eskisehireo.org.tr/eskisehir-nobetci-eczaneler"
    response = requests.get(url, timeout=60)
    soup = BeautifulSoup(response.text, "html.parser")
    pharmacies = soup.find_all("div", class_="nobetci")

    data = []  # To store extracted data

    for pharmacy in pharmacies:
        # Extract name
        h4_tag: Tag | None = pharmacy.find("h4", class_="text-danger")

        if h4_tag is None:
            continue

        name = h4_tag.text.strip()

        district = _get_district_from_name(name) if name else None

        name = name.split("-")[0].strip()

        # Address
        address_tag = pharmacy.find("i", class_="fa-home")
        if address_tag:
            address = address_tag.next_sibling.strip()  # The text after the <i> icon
        else:
            address = None

        # Phone
        phone_tag = pharmacy.find(
            "a", href=lambda href: href and href.startswith("tel:")
        )
        phone = phone_tag.text.strip() if phone_tag else None

        # Google Maps Location
        map_tag = pharmacy.find(
            "a", href=lambda href: href and "google.com/maps" in href
        )
        google_maps = map_tag["href"] if map_tag else None
        coordinates = (
            get_coordinates_from_google_maps_url(google_maps) if google_maps else None
        )

        # Operation Times
        operation_time_tag = pharmacy.find("span", class_="text-danger")
        operation_times = (
            operation_time_tag.text.strip() if operation_time_tag else None
        )
        start_date, end_date = (
            _get_duty_dates(operation_times) if operation_times else (None, None)
        )

        # Append to the data list
        data.append(
            {
                "name": name,
                "address": address,
                "district": district,
                "phone": phone,
                "coordinates": coordinates,
                "duty_start": start_date,
                "duty_end": end_date,
            }
        )

    return data


if __name__ == "__main__":
    eskisehir_data = get_eskisehir_data()
    for entry in eskisehir_data:
        print(entry)
