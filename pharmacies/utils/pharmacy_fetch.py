import requests
import json

"""
This script was to fetch all pharmacies in a city using Google Places API
But due the restrictions of API that only allows fetch 60 pharmacies at a
query (even with the pagination it provides), decided that this is not feasible
"""


def fetch_pharmacies_in_eskisehir(api_key, page_size=20):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "*",
    }

    data = {"textQuery": "pharmacy in eskisehir", "pageSize": page_size}

    results = []
    next_page_token = None

    while True:
        if next_page_token:
            import time

            time.sleep(2)
            data["pageToken"] = next_page_token
        else:
            data.pop("pageToken", None)

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_data = response.json()
            results.extend(response_data.get("places", []))
            next_page_token = response_data.get("nextPageToken")

            if not next_page_token:
                break
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break

    return results


def save_to_json(data, filename="pharmacies_in_eskisehir.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

    pharmacies = fetch_pharmacies_in_eskisehir(api_key)
    save_to_json(pharmacies)
    print(f"Saved {len(pharmacies)} pharmacies to pharmacies_in_eskisehir.json")
