"""
Scraper for Eskişehir Eczacı Odası (EEO).

Fetches duty pharmacy data from the official Eskişehir Chamber of Pharmacists website.
"""

from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


def _get_district_from_name(pharmacy_name: str) -> str:
    """Extract district name from pharmacy name (e.g., 'X Pharmacy - Odunpazarı')."""
    return pharmacy_name.split(" ")[-1]


def _get_duty_dates(operation_times: str) -> tuple[datetime, datetime]:
    """
    Parse duty start and end dates from the operation times string.

    Format: "DD.MM.YYYY HH:MM - DD.MM.YYYY HH:MM"
    """
    parts = operation_times.split(" ")
    start_date = datetime.strptime(parts[0] + " " + parts[1], "%d.%m.%Y %H:%M")
    end_date = datetime.strptime(parts[3] + " " + parts[4], "%d.%m.%Y %H:%M")
    return start_date, end_date


def get_eskisehir_data() -> list[dict[str, Any]]:
    """
    Scrape pharmacy data from the Eskişehir Eczacı Odası website.

    Extracts name, address, district, phone, coordinates, and duty times.
    """
    from pharmacies.utils.utils import get_coordinates_from_google_maps_url

    url = "https://www.eskisehireo.org.tr/eskisehir-nobetci-eczaneler"
    response = requests.get(url, timeout=60)
    soup = BeautifulSoup(response.text, "html.parser")
    pharmacies = soup.find_all("div", class_="nobetci")

    data: list[dict[str, Any]] = []  # To store extracted data

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
        address: str | None = None
        if address_tag:
            next_sibling = address_tag.next_sibling
            if next_sibling:
                address = str(next_sibling).strip()  # The text after the <i> icon

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

        coordinates: dict[str, float] | None = None
        if google_maps and isinstance(google_maps, str):
            coordinates = get_coordinates_from_google_maps_url(google_maps)

        # Operation Times
        operation_time_tag = pharmacy.find("span", class_="text-danger")
        operation_times = (
            operation_time_tag.text.strip() if operation_time_tag else None
        )

        start_date: datetime | None = None
        end_date: datetime | None = None

        if operation_times:
            start_date, end_date = _get_duty_dates(operation_times)

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
