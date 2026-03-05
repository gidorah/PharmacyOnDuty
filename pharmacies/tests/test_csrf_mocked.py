import json
from unittest.mock import MagicMock, patch
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse
from pharmacies.models import PharmacyStatus

@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class TestCSRFProtection(SimpleTestCase):
    def test_get_pharmacy_points_csrf_enforced(self):
        """
        Test that accessing the endpoint without a CSRF token returns 403 Forbidden.
        """
        client = Client(enforce_csrf_checks=True)
        url = reverse("pharmacies:get_pharmacy_points")

        response = client.post(
            url,
            data=json.dumps({"lat": 39.7, "lng": 30.5}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("pharmacies.views.get_city_name_from_location")
    @patch("pharmacies.views.City.objects.get")
    @patch("pharmacies.views.get_nearest_pharmacies_open")
    def test_get_pharmacy_points_with_csrf_token(
        self,
        mock_fetch_open,
        mock_city_get,
        mock_get_city_name,
    ):
        """
        Test that accessing the endpoint WITH a valid CSRF token works (200 OK).
        We mock out all DB and external API calls.

        Note on Mock Order:
        Decorators are applied bottom-up.
        1. @patch("...get_nearest_pharmacies_open") (Bottom) -> First Argument (mock_fetch_open)
        2. @patch("...City.objects.get") (Middle) -> Second Argument (mock_city_get)
        3. @patch("...get_city_name_from_location") (Top) -> Third Argument (mock_get_city_name)
        """
        client = Client(enforce_csrf_checks=True)

        # Setup mocks
        mock_get_city_name.return_value = "eskisehir"

        mock_city = MagicMock()
        mock_city.get_city_status.return_value = PharmacyStatus.OPEN
        mock_city_get.return_value = mock_city

        mock_fetch_open.return_value = []

        url = reverse("pharmacies:get_pharmacy_points")

        # Get CSRF token from home page
        response = client.get(reverse("home"))
        self.assertIn("csrftoken", response.cookies)
        csrftoken = response.cookies["csrftoken"].value

        with patch("django.utils.timezone.now"):
            response = client.post(
                url,
                data=json.dumps({"lat": 39.7, "lng": 30.5}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=csrftoken,
            )

        self.assertEqual(response.status_code, 200)
