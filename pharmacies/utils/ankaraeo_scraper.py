from datetime import datetime, timedelta

import requests
from django.utils import timezone


def _get_duty_times():
    current_time = timezone.now()

    if (
        current_time.weekday() == 6 and current_time.hour >= 6
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


def get_ankara_data():
    """
    Scrape pharmacy data from the Ankara Eczacılar Odası website.
    Returns a list of dictionaries with name, address, district, phone, coordinates.
    """
    base_url = "https://mvc.aeo.org.tr/home/NobetciEczaneGetirTarih?nobetTarihi="
    today = datetime.now()
    url = base_url + today.strftime("%Y-%m-%d")
    response = requests.get(url, timeout=10)

    received_data = response.json()
    received_pharmacy_list = received_data["NobetciEczaneBilgisiListesi"]
    duty_start, duty_end = _get_duty_times()
    pharmacies = []
    for pharmacy in received_pharmacy_list:
        pharmacies.append(
            {
                "name": pharmacy["EczaneAdi"].title() + " Eczanesi",
                "address": pharmacy["EczaneAdresi"],
                "district": pharmacy["IlceAdi"],
                "phone": pharmacy["Telefon"],
                "coordinates": {
                    "lat": float(pharmacy["KoordinatLat"]),
                    "lng": float(pharmacy["KoordinatLng"]),
                },
                "duty_start": duty_start,
                "duty_end": duty_end,
            }
        )

    return pharmacies


if __name__ == "__main__":
    # If you have the HTML saved to a file, you can do something like:
    # with open("crisis-pha.html", "r", encoding="utf-8") as f:
    #     html_content = f.read()

    # Or if you want to fetch directly from the website (live scrape):
    # response = requests.get("https://www.aeo.org.tr/crisis-pha")
    # html_content = response.text

    # For demonstration, we'll assume you have your full HTML in a string:
    html_content = """\
    <!-- Paste or read your attached HTML content here -->
    """

    pharmacies_data = get_ankara_data()

    # Print or handle the scraped data
    for pharmacy in pharmacies_data:
        print(pharmacy)
