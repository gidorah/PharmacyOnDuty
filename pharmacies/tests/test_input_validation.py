import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from pharmacies.models import PharmacyStatus
from pharmacies.views import get_pharmacy_points


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


@patch("pharmacies.views.City")
@patch("pharmacies.views.get_city_name_from_location")
def test_invalid_coordinates(
    mock_get_city: MagicMock, mock_city_model: MagicMock, rf: RequestFactory
) -> None:
    """Test that invalid coordinates return a 400 error."""

    # Fix for catching City.DoesNotExist which becomes a Mock
    mock_city_model.DoesNotExist = Exception

    mock_get_city.return_value = "Test City"
    mock_city_model.objects.get.return_value = MagicMock()

    # Test latitude > 90
    data = {"lat": 91.0, "lng": 30.0}
    request = rf.post(
        "/get_pharmacy_points", data=json.dumps(data), content_type="application/json"
    )

    # We patch the database access inside the view entirely just in case
    with patch("pharmacies.views.get_nearest_pharmacies_open", return_value=[]):
        response = get_pharmacy_points(request)

    assert (
        response.status_code == 400
    ), f"Expected 400 for invalid lat, got {response.status_code}"
    # The error message content checking is what we want to verify
    assert b"Invalid coordinates" in response.content


@patch("pharmacies.views.City")
@patch("pharmacies.views.get_city_name_from_location")
def test_valid_coordinates(
    mock_get_city: MagicMock, mock_city_model: MagicMock, rf: RequestFactory
) -> None:
    """Test that valid coordinates proceed (mocking the rest)."""
    mock_city_model.DoesNotExist = Exception

    mock_get_city.return_value = "Test City"
    mock_city_instance = MagicMock()
    # Assuming PharmacyStatus.OPEN is handled/mocked correctly.
    # The view checks: if city_status == PharmacyStatus.OPEN
    mock_city_instance.get_city_status.return_value = PharmacyStatus.OPEN
    mock_city_model.objects.get.return_value = mock_city_instance

    with patch("pharmacies.views.get_nearest_pharmacies_open", return_value=[]):
        data = {"lat": 40.0, "lng": 30.0}
        request = rf.post(
            "/get_pharmacy_points",
            data=json.dumps(data),
            content_type="application/json",
        )
        response = get_pharmacy_points(request)

        assert response.status_code == 200
