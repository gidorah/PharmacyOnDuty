import json
from datetime import UTC, datetime, time
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse

from pharmacies.models import City, WorkingSchedule


@pytest.mark.django_db
class TestGetPharmacyPoints:
    @pytest.fixture
    def setup_city(self) -> City:
        city = City.objects.create(name="eskisehir")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )
        return city

    def test_get_pharmacy_points_not_post(self, client: Client) -> None:
        url = reverse("pharmacies:get_pharmacy_points")
        response = client.get(url)
        assert response.status_code == 405

    @patch("pharmacies.views.get_city_name_from_location")
    @patch("pharmacies.views.get_nearest_pharmacies_open")
    def test_get_pharmacy_points_open_success(
        self,
        mock_fetch_open: MagicMock,
        mock_get_city: MagicMock,
        client: Client,
        setup_city: City,
    ) -> None:
        mock_get_city.return_value = "eskisehir"
        mock_fetch_open.return_value = [
            {"title": "Open Pharmacy", "position": {"lat": 39.7, "lng": 30.5}}
        ]

        url = reverse("pharmacies:get_pharmacy_points")

        # Tuesday 10:00 (Open)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime(2025, 12, 16, 10, 0, tzinfo=UTC)

            response = client.post(
                url,
                data=json.dumps({"lat": 39.7, "lng": 30.5}),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.json()
        assert "points" in data
        assert data["points"][0]["title"] == "Open Pharmacy"

    @patch("pharmacies.views.get_city_name_from_location")
    @patch("pharmacies.views.get_nearest_pharmacies_on_duty")
    def test_get_pharmacy_points_on_duty_success(
        self,
        mock_fetch_duty: MagicMock,
        mock_get_city: MagicMock,
        client: Client,
        setup_city: City,
    ) -> None:
        mock_get_city.return_value = "eskisehir"
        mock_fetch_duty.return_value = [
            {"title": "Duty Pharmacy", "position": {"lat": 39.7, "lng": 30.5}}
        ]

        url = reverse("pharmacies:get_pharmacy_points")

        # Tuesday 20:00 (Closed -> On Duty)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime(2025, 12, 16, 20, 0, tzinfo=UTC)

            response = client.post(
                url,
                data=json.dumps({"lat": 39.7, "lng": 30.5}),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.json()
        assert "points" in data
        assert data["points"][0]["title"] == "Duty Pharmacy"

    def test_get_pharmacy_points_invalid_json(self, client: Client) -> None:
        url = reverse("pharmacies:get_pharmacy_points")
        response = client.post(
            url, data="invalid-json", content_type="application/json"
        )
        assert (
            response.status_code == 400
        )  # JSONDecodeError (ValueError) caught in view

    @patch("pharmacies.views.get_city_name_from_location")
    def test_get_pharmacy_points_city_not_found(
        self, mock_get_city: MagicMock, client: Client
    ) -> None:
        mock_get_city.return_value = "unknown_city"
        url = reverse("pharmacies:get_pharmacy_points")

        response = client.post(
            url,
            data=json.dumps({"lat": 39.7, "lng": 30.5}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "City matching query does not exist" in response.json()["error"]


@pytest.mark.django_db
class TestOtherViews:
    def test_pharmacies_list(self, client: Client) -> None:
        url = reverse("home")
        response = client.get(url)
        assert response.status_code == 200
        assert "pharmacies.html" in [t.name for t in response.templates]

    def test_google_maps_proxy_not_get(self, client: Client) -> None:
        url = reverse("pharmacies:google_maps_proxy")
        response = client.post(url)
        assert response.status_code == 405

    def test_google_maps_proxy_forbidden(self, client: Client) -> None:
        url = reverse("pharmacies:google_maps_proxy")
        response = client.get(url, HTTP_REFERER="http://malicious.com")
        assert response.status_code == 403

    @patch("pharmacies.views.requests.get")
    def test_google_maps_proxy_success(
        self, mock_get: MagicMock, client: Client
    ) -> None:
        mock_response = MagicMock()
        mock_response.text = "console.log('google maps');"
        mock_get.return_value = mock_response

        url = reverse("pharmacies:google_maps_proxy")
        # Referer check needs to pass.
        # In settings.py, ALLOWED_REFERERS might contain localhost or similar.
        with patch("pharmacies.views.is_allowed_referer", return_value=True):
            response = client.get(url)

        assert response.status_code == 200
        assert response.content == b"console.log('google maps');"
        assert response["Content-Type"] == "text/javascript"
