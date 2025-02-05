import csv
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

BASE_URL = "https://nobetcieczane.istanbulsaglik.gov.tr:88/"
API_ENDPOINT = f"{BASE_URL}Home/GetEczaneler"


DISTRICTS: list[str] = [
    "Adalar",
    "Arnavutköy",
    "Ataşehir",
    "Avcılar",
    "Bağcılar",
    "Bahçelievler",
    "Bakırköy",
    "Başakşehir",
    "Bayrampaşa",
    "Beşiktaş",
    "Beykoz",
    "Beylikdüzü",
    "Beyoğlu",
    "Büyükçekmece",
    "Çatalca",
    "Çekmeköy",
    "Esenler",
    "Esenyurt",
    "Eyüp",
    "Fatih",
    "Gaziosmanpaşa",
    "Güngören",
    "Kadıköy",
    "Kağıthane",
    "Kartal",
    "Küçükçekmece",
    "Maltepe",
    "Pendik",
    "Sancaktepe",
    "Sarıyer",
    "Silivri",
    "Sultanbeyli",
    "Sultangazi",
    "Şile",
    "Şişli",
    "Tuzla",
    "Ümraniye",
    "Üsküdar",
    "Zeytinburnu",
]


def _get_coordinates_from_sehirharitasi_url(url: str):
    #  href="http://sehirharitasi.ibb.gov.tr/?lat=41.01569563781570&amp;lon=28.89617195242220&amp;zoom=18

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    lat = query_params.get("lat", [""])[0]
    lon = query_params.get("lon", [""])[0]

    return {"lat": float(lat), "lng": float(lon)}


def _get_duty_times():
    current_time = timezone.now()

    if (
        current_time.weekday == 6 and current_time.hour >= 6
    ):  # If it's Sunday, pharmacies are open all day until 9am tomorrow
        duty_start = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        duty_end = current_time.replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        return duty_start, duty_end

    if (
        current_time.hour < 6
    ):  # If it's before 9am, pharmacies are in duty of the previous day
        current_time = current_time - timedelta(days=1)

    duty_start = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
    duty_end = current_time.replace(
        hour=6, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    return duty_start, duty_end


def get_istanbul_data():
    all_pharmacies = []

    for district_name in DISTRICTS:
        payload = {"ilce": district_name}
        response = requests.post(API_ENDPOINT, params=payload, timeout=10)

        if response.status_code != 200:
            print(
                f"Error fetching data for district {district_name}: {response.status_code}"
            )
            continue

        html_content = response.content.decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")
        pharmacy_cards = soup.select(".card")
        for card in pharmacy_cards:
            pharmacy = {"district": district_name}

            # Extract name
            name_tag = card.find_all(name="div", class_="card-header")[1].select_one(
                "b"
            )
            pharmacy["name"] = name_tag.text.strip() if name_tag else "N/A"

            # Extract phone
            tel_tag = card.find_all(name="label")[1]
            phone_tag = tel_tag.select_one("a")
            pharmacy["phone"] = (
                phone_tag.text.strip().replace(" ", "") if phone_tag else "N/A"
            )

            # Extract address
            address_label_tag = card.find(name="i", class_="la la-home")
            address_tag = address_label_tag.find_next("label")
            pharmacy["address"] = address_tag.text.strip() if address_tag else "N/A"

            # Extract coordinates
            directions_tag = card.find(name="a", class_="btn btn-primary btn-block")
            directions_url = directions_tag["href"] if directions_tag else "N/A"
            coordinates = _get_coordinates_from_sehirharitasi_url(directions_url)
            pharmacy["coordinates"] = coordinates

            # Set duty times
            pharmacy["duty_start"], pharmacy["duty_end"] = _get_duty_times()
            all_pharmacies.append(pharmacy)

    return all_pharmacies


def save_to_csv(data, filename="pharmacies.csv"):
    keys = data[0].keys() if data else []
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    pharmacies = get_istanbul_data()
    save_to_csv(pharmacies)
    print(f"Collected {len(pharmacies)} pharmacy records")
