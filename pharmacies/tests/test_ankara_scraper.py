import json
from collections.abc import Iterator
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from pharmacies.models import City, WorkingSchedule
from pharmacies.utils.ankaraeo_scraper import (
    AnkaraScraperError,
    _turkish_title,
    get_ankara_data,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ankaraeo_getpharmacies.json"
DUTY_START = datetime(2026, 10, 26, 16, 0, tzinfo=UTC)
DUTY_END = datetime(2026, 10, 27, 6, 0, tzinfo=UTC)


def _load_fixture() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data


@pytest.fixture(autouse=True)
def _fixed_duty_window(request: pytest.FixtureRequest) -> Iterator[None]:
    """Keep scraper tests off the database, except the ones that opt in."""
    if request.node.get_closest_marker("django_db"):
        yield
        return
    with patch(
        "pharmacies.utils.ankaraeo_scraper.get_duty_window",
        return_value=(DUTY_START, DUTY_END),
    ):
        yield


def _json_response(payload: Any) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.is_redirect = False
    response.headers = {"Content-Type": "text/html; charset=UTF-8"}
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("YENİ ÜMİT", "Yeni Ümit"),
        ("NEHİR MURAT", "Nehir Murat"),
        ("CENGİZ", "Cengiz"),
        ("ŞİFA", "Şifa"),
        ("SAĞLIK", "Sağlık"),
        ("ÇINAR", "Çınar"),
        ("AKYURT MERKEZ", "Akyurt Merkez"),
        ("Yeni Ümit", "Yeni Ümit"),
        ("AYŞE-NUR", "Ayşe-Nur"),
        ("DR.AHMET", "Dr.Ahmet"),
        ("(YENİ)", "(Yeni)"),
        ("İLKER", "İlker"),
        ("IŞIK", "Işık"),
    ],
)
def test_turkish_title_cases_turkish_letters(raw: str, expected: str) -> None:
    result = _turkish_title(raw)

    assert result == expected
    assert "\u0307" not in result


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_parses_get_pharmacies_html(mock_get: MagicMock) -> None:
    mock_get.return_value = _json_response(_load_fixture())

    data = get_ankara_data()

    assert len(data) == 3
    assert data[0] == {
        "name": "Emek Sağlık Eczanesi",
        "address": "Emek Mah. Kırım Cad. No:80/C Çankaya/ ANKARA",
        "district": "Çankaya",
        "phone": "3122211770",
        "coordinates": {"lat": 39.924390797592, "lng": 32.815630913887},
        "duty_start": DUTY_START,
        "duty_end": DUTY_END,
    }
    assert data[1]["name"] == "Çınar Eczanesi"
    assert data[1]["phone"] == "3123123334"
    assert data[1]["coordinates"] == {"lat": 39.909901855431, "lng": 32.796953469515}
    assert data[2]["name"] == "Akyurt Merkez Eczanesi"
    assert data[2]["district"] == "Akyurt"
    assert data[2]["phone"] == "3125122612"
    assert data[2]["coordinates"] == {"lat": 40.13111297929, "lng": 33.080611489713}
    assert all("\u0307" not in item["name"] for item in data)


@pytest.mark.parametrize(
    ("now", "url_date", "start", "end"),
    [
        # 00:00 TRT Thu: still Wednesday night's duty
        (
            datetime(2026, 10, 28, 21, 0, tzinfo=UTC),
            "2026-10-28",
            datetime(2026, 10, 28, 15, 30, tzinfo=UTC),
            datetime(2026, 10, 29, 6, 0, tzinfo=UTC),
        ),
        # 02:00 TRT Thu
        (
            datetime(2026, 10, 28, 23, 0, tzinfo=UTC),
            "2026-10-28",
            datetime(2026, 10, 28, 15, 30, tzinfo=UTC),
            datetime(2026, 10, 29, 6, 0, tzinfo=UTC),
        ),
        # 05:00 TRT Thu
        (
            datetime(2026, 10, 29, 2, 0, tzinfo=UTC),
            "2026-10-28",
            datetime(2026, 10, 28, 15, 30, tzinfo=UTC),
            datetime(2026, 10, 29, 6, 0, tzinfo=UTC),
        ),
        # 17:00 TRT Thu
        (
            datetime(2026, 10, 29, 14, 0, tzinfo=UTC),
            "2026-10-29",
            datetime(2026, 10, 29, 15, 30, tzinfo=UTC),
            datetime(2026, 10, 30, 6, 0, tzinfo=UTC),
        ),
        # Sunday daytime
        (
            datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
            "2026-11-01",
            datetime(2026, 11, 1, 6, 0, tzinfo=UTC),
            datetime(2026, 11, 2, 6, 0, tzinfo=UTC),
        ),
    ],
)
@pytest.mark.django_db
@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_requests_the_list_of_the_duty_windows_date(
    mock_get: MagicMock,
    now: datetime,
    url_date: str,
    start: datetime,
    end: datetime,
) -> None:
    city = City.objects.create(name="ankara")
    WorkingSchedule.objects.create(
        city=city,
        weekday_start=time(5, 30),
        weekday_end=time(15, 30),
        saturday_start=time(7, 0),
        saturday_end=time(15, 0),
    )
    mock_get.return_value = _json_response(_load_fixture())

    with patch("pharmacies.utils.duty_window.timezone.now", return_value=now):
        data = get_ankara_data()

    mock_get.assert_called_once_with(
        f"https://www.aeo.org.tr/getPharmacies/{url_date}",
        timeout=10,
        allow_redirects=False,
    )
    assert len(data) == 3
    assert all(item["duty_start"] == start for item in data)
    assert all(item["duty_end"] == end for item in data)


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_redirect_raises_scraper_error(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 301
    response.is_redirect = True
    response.headers = {"Location": "https://mvc.aeo.org.tr/admin"}
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    with pytest.raises(AnkaraScraperError) as exc_info:
        get_ankara_data()

    assert isinstance(exc_info.value, requests.exceptions.RequestException)
    assert "301" in str(exc_info.value)
    assert "https://mvc.aeo.org.tr/admin" in str(exc_info.value)


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_non_json_body_raises_scraper_error(
    mock_get: MagicMock,
) -> None:
    response = _json_response(None)
    response.text = "<!DOCTYPE html><html><body>admin</body></html>"
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Expecting value", response.text, 0
    )
    mock_get.return_value = response

    with pytest.raises(AnkaraScraperError) as exc_info:
        get_ankara_data()

    assert not isinstance(exc_info.value, requests.exceptions.JSONDecodeError)


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_error_status_raises_with_upstream_message(
    mock_get: MagicMock,
) -> None:
    message = "Maksimum bugün dahil 10 günlük nöbet verisi gösterilmektedir."
    mock_get.return_value = _json_response({"status": "error", "message": message})

    with pytest.raises(AnkaraScraperError, match=message):
        get_ankara_data()


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_http_error_propagates(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 500
    response.is_redirect = False
    response.headers = {}
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    mock_get.return_value = response

    with pytest.raises(requests.exceptions.HTTPError):
        get_ankara_data()


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_skips_entries_without_valid_coordinates(
    mock_get: MagicMock,
) -> None:
    def box(name: str, maps_link: str) -> str:
        return (
            f'<div class="inline-box" data-name="{name}" data-district="Çankaya">'
            f'<div class="text"><h4>{name} ECZANESİ</h4>'
            f"<p>Some Mah. No:1 Çankaya/ ANKARA <br>near <span>0312000000</span>"
            f'</p></div><div class="right">{maps_link}</div></div>'
        )

    html = (
        '<div class="petition-list">'
        + box("NO LINK", "")
        + box(
            "BAD COORDS",
            '<a href="https://www.google.com/maps/search/?api=1&query=abc,def">x</a>',
        )
        + box(
            "GOOD",
            '<a href="https://www.google.com/maps/search/?api=1&query=39.9,32.8">x</a>',
        )
        + "</div>"
    )
    mock_get.return_value = _json_response({"status": "success", "html": html})

    data = get_ankara_data()

    assert [pharmacy["name"] for pharmacy in data] == ["Good Eczanesi"]
    assert data[0]["coordinates"] == {"lat": 39.9, "lng": 32.8}


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_no_entries_returns_empty(mock_get: MagicMock) -> None:
    html = (
        '<div class="petition-list"></div>'
        '<div class="petition-list-not-found">'
        "<h4>Nöbetçi Eczane Bulunamadı</h4></div>"
    )
    mock_get.return_value = _json_response({"status": "success", "html": html})

    assert get_ankara_data() == []


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
def test_get_ankara_data_normalizes_phone_to_stored_format(
    mock_get: MagicMock,
) -> None:
    # Rows stored from the old AEO API keep phones as digits without leading
    # zeros; ingest matches on (name, phone), so scraped phones must agree.
    def box(name: str, phone: str) -> str:
        return (
            f'<div class="inline-box" data-name="{name}" data-district="Çankaya">'
            f'<div class="text"><h4>{name} ECZANESİ</h4>'
            f"<p>Some Mah. No:1 Çankaya/ ANKARA <br>near <span>{phone}</span></p>"
            '</div><div class="right"><a href="https://www.google.com/maps/search/'
            '?api=1&query=39.9,32.8">x</a></div></div>'
        )

    html = (
        '<div class="petition-list">'
        + box("SPACED", "0312 230 23 12")
        + box("MOBILE", "0533 301 54 04")
        + box("DOUBLE ZERO", "00312 728 15 33")
        + box("NO DIGITS", "-")
        + "</div>"
    )
    mock_get.return_value = _json_response({"status": "success", "html": html})

    data = get_ankara_data()

    assert [(pharmacy["name"], pharmacy["phone"]) for pharmacy in data] == [
        ("Spaced Eczanesi", "3122302312"),
        ("Mobıle Eczanesi", "5333015404"),
        ("Double Zero Eczanesi", "3127281533"),
    ]
