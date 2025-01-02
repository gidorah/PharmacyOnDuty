import requests
from bs4 import BeautifulSoup


def get_eskisehir_data():
    url = "https://www.eskisehireo.org.tr/eskisehir-nobetci-eczaneler"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    pharmacies = soup.find_all("div", class_="nobetci")

    data = []  # To store extracted data

    for pharmacy in pharmacies:
        # Extract name
        name = pharmacy.find("h4", class_="text-danger").text.strip()

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

        # Operation Times
        operation_time_tag = pharmacy.find("span", class_="text-danger")
        if operation_time_tag:
            operation_times = operation_time_tag.text.strip()
        else:
            operation_times = None

        # Append to the data list
        data.append(
            {
                "name": name,
                "address": address,
                "phone": phone,
                "google_maps": google_maps,
                "operation_times": operation_times,
            }
        )

    return data


if __name__ == "__main__":
    eskisehir_data = get_eskisehir_data()
    for entry in eskisehir_data:
        print(entry)
