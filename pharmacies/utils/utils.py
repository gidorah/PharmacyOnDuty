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
