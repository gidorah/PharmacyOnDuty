from datetime import datetime, time, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from django.utils import timezone


def _get_duty_times(testing=True):
    if testing:
        current_time = datetime.now()
    else:
        current_time = timezone.now()

    duty_start = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
    duty_end = current_time.replace(
        hour=9, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    return duty_start, duty_end


def get_istanbul_data() -> list[dict]:
    url = "https://istanbul.eczaneleri.org/"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    active_list_div: Tag | NavigableString | None = soup.find("div", class_="active")

    print(type(active_list_div))

    if not isinstance(active_list_div, Tag):
        return []

    pharmacies_ul = active_list_div.find("ul", class_="media-list")

    if not isinstance(pharmacies_ul, Tag):
        return []

    pharmacies = pharmacies_ul.find_all("div", class_="media-body")

    data = []  # To store extracted data

    for pharmacy in pharmacies:
        name = pharmacy.h4.find(text=True, recursive=False).strip()
        address = pharmacy.a.find_next_sibling(text=True).strip().replace("<br>", "")

        pharmacy_url = urljoin(url, pharmacy.a.get("href"))

        response = requests.get(pharmacy_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        button_data = soup.find(name="button", id="navigationRoadBtn")

        if isinstance(button_data, Tag):
            lat = button_data.attrs["lat"]
            lng = button_data.attrs["lng"]
            coordinates = {"lat": float(lat), "lng": float(lng)}

        phone_tag = soup.select_one('a[href^="tel:"]')

        if isinstance(phone_tag, Tag):
            phone = phone_tag.text.strip()

        duty_start, duty_end = _get_duty_times()

        data.append(
            {
                "name": name,
                "address": address,
                "district": address.split(" ")[-1],
                "phone": phone if phone else "",
                "coordinates": coordinates if coordinates else "",
                "duty_start": duty_start,
                "duty_end": duty_end,
            }
        )

    return data


if __name__ == "__main__":
    data = get_istanbul_data()
    for entry in data:
        print(entry)
