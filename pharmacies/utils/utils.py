def get_coordinates_from_google_maps_url(url: str):
    coordinate_string = url.split("=")[-1]
    lat = float(coordinate_string.split(",")[0])
    lng = float(coordinate_string.split(",")[1])
    coordinates = {"lat": lat, "lng": lng}
    return coordinates


def get_map_points_from_scraped_data(scraped_data):
    map_points = []

    for item in scraped_data:
        point = {
            "position": get_coordinates_from_google_maps_url(item["google_maps"]),
            "title": item["name"],
            "description": item["address"],
        }
        map_points.append(point)
    return map_points


def fetch_all_pharmacies_in_city(city: str):
    import requests
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Get the API key from environment variables
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("Google Maps API key not found in environment variables.")

    # Initialize results list and pagination token
    results = []
    next_page_token = None

    while True:
        # Prepare the API request URL
        formatted_city = city.lower().replace(" ", "+")
        page_token_str = f"&pagetoken={next_page_token}" if next_page_token else ""
        endpoint = (
            f"https://maps.googleapis.com/maps/api/place/textsearch/json?"
            f"query=pharmacies+in+{formatted_city}&key={api_key}{page_token_str}"
        )

        # Make the API request
        response = requests.get(endpoint)

        # Check for a successful response, raise exception for HTTP errors
        if response.status_code != 200:
            raise Exception(f"Error fetching data from Google API: {response.text}")

        # Extract data from the response
        response_data = response.json()
        results.extend(response_data.get("results", []))

        # Check for the next page token (if any)
        next_page_token = response_data.get("next_page_token")

        # Wait briefly if the next_page_token is provided (per Google API docs)
        if next_page_token:
            import time

            time.sleep(2)  # To avoid quota issues with rapid requests

        # If no next page, break the loop
        if not next_page_token:
            break

    return results


if __name__ == "__main__":
    import json

    # Fetch pharmacies for a given city
    city_name = "eskisehir"
    pharmacies = fetch_all_pharmacies_in_city(city_name)

    # Save results to a JSON file
    with open(f"{city_name.lower().replace(' ', '_')}_pharmacies.json", "w") as file:
        json.dump(pharmacies, file, indent=4)
