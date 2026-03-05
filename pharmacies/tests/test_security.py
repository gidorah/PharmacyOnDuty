import json
from datetime import time
import pytest
from django.test import Client
from django.urls import reverse
from pharmacies.models import City, WorkingSchedule

@pytest.mark.django_db
class TestCSRFProtection:
    @pytest.fixture
    def setup_city(self):
        city, _ = City.objects.get_or_create(name="eskisehir")
        WorkingSchedule.objects.get_or_create(
            city=city,
            defaults={
                "weekday_start": time(9, 0),
                "weekday_end": time(18, 0),
                "saturday_start": time(9, 0),
                "saturday_end": time(13, 0),
            }
        )
        return city

    def test_get_pharmacy_points_csrf_enforced(self, setup_city):
        """
        Test that get_pharmacy_points rejects requests without a CSRF token.
        When CSRF protection is enabled, this should return 403.
        When disabled (vulnerable), it returns 200.
        """
        # Enforce CSRF checks in the client
        client = Client(enforce_csrf_checks=True)
        url = reverse("pharmacies:get_pharmacy_points")

        # payload
        data = {"lat": 39.7767, "lng": 30.5206}

        # Attempt POST without CSRF token
        response = client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )

        # Should be forbidden (403) if CSRF is working
        assert response.status_code == 403

    def test_get_pharmacy_points_with_csrf_token(self, setup_city):
        """
        Test that get_pharmacy_points accepts requests with a valid CSRF token.
        This ensures legitimate requests are not blocked.
        """
        client = Client(enforce_csrf_checks=True)

        # Visit home page to get CSRF cookie
        response_home = client.get(reverse("home"))
        assert response_home.status_code == 200
        assert "csrftoken" in response_home.cookies, "CSRF cookie not set on home page"

        csrftoken = response_home.cookies["csrftoken"].value

        url = reverse("pharmacies:get_pharmacy_points")
        data = {"lat": 39.7767, "lng": 30.5206}

        # Send POST with X-CSRFToken header
        response = client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrftoken
        )

        # Should be 200 OK (or at least not 403)
        # Note: Depending on mock setup or data, it might fail logic inside view, but shouldn't fail CSRF check.
        # However, setup_city should allow it to pass logic checks partially.
        # If GDAL is missing, this will crash with ImportError or ImproperlyConfigured during view execution.
        # But we assert != 403 to prove CSRF passed.

        if response.status_code == 403:
            pytest.fail("CSRF check failed even with token")

        # We don't assert 200 strictly because of the GDAL issue preventing full execution.
        # But if the view executes and crashes inside, it returns 500 or raises exception.
        # If it returns 403, it means CSRF rejected it.
