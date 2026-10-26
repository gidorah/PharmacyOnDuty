"""
Scraper for Ankara Eczacılar Odası (AEO).

Fetches duty pharmacy data from the chamber's public ``getPharmacies`` endpoint
(the one behind https://www.aeo.org.tr/nobetci-eczaneler). It answers with a JSON
object whose ``html`` field holds one ``div.inline-box`` per duty pharmacy; the
pharmacy fields are parsed out of that HTML fragment.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from django.utils import timezone

logger = logging.getLogger(__name__)

BASE_URL = "https://www.aeo.org.tr/getPharmacies/"


class AnkaraScraperError(requests.exceptions.RequestException):
    """The AEO endpoint answered with something other than duty pharmacy data."""


def _get_duty_times() -> tuple[datetime, datetime]:
    """
    Calculate the start and end times for the duty shift.

    Duty shifts typically start at 18:30 or 19:00 (handled here as 16:00 UTC?)
    and end at 08:30 or 09:00 the next day.
    """
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


def _collapse(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip the ends."""
    return " ".join(text.split())


def _parse_coordinates(box: Tag) -> dict[str, float] | None:
    """Read ``lat,lng`` from the ``query`` parameter of the Google Maps link."""
    link = box.find("a", href=lambda href: bool(href) and "google.com/maps" in href)
    if not isinstance(link, Tag):
        return None
    query = parse_qs(urlparse(str(link.get("href", ""))).query).get("query")
    if not query:
        return None
    parts = query[0].split(",")
    if len(parts) != 2:
        return None
    try:
        return {"lat": float(parts[0]), "lng": float(parts[1])}
    except ValueError:
        return None


def _parse_pharmacy(
    box: Tag, duty_start: datetime, duty_end: datetime
) -> dict[str, Any] | None:
    """Turn one ``div.inline-box`` into the standardized pharmacy dict."""
    name = _collapse(str(box.get("data-name", "")))
    paragraph = box.find("p")
    phone_tag = paragraph.find("span") if isinstance(paragraph, Tag) else None
    raw_phone = phone_tag.get_text() if isinstance(phone_tag, Tag) else ""
    # Rows stored from the old AEO API keep phones as bare digits without
    # leading zeros ("3127121829"); ingest matches on (name, phone), so the new
    # source's "0312 712 18 29" / "00312 ..." forms must be normalized to match.
    phone = "".join(char for char in raw_phone if char in "0123456789").lstrip("0")
    coordinates = _parse_coordinates(box)
    if not name or not phone or coordinates is None:
        logger.warning(
            "Skipping Ankara pharmacy entry with missing name, phone or "
            "coordinates: %r",
            name,
        )
        return None

    address = ""
    if isinstance(paragraph, Tag):
        address_parts: list[str] = []
        for child in paragraph.children:
            if isinstance(child, Tag) and child.name in ("br", "span"):
                break
            address_parts.append(
                child.get_text() if isinstance(child, Tag) else str(child)
            )
        address = _collapse("".join(address_parts))

    return {
        "name": name.title() + " Eczanesi",
        "address": address,
        "district": str(box.get("data-district", "")).strip(),
        "phone": phone,
        "coordinates": coordinates,
        "duty_start": duty_start,
        "duty_end": duty_end,
    }


def get_ankara_data() -> list[dict[str, Any]]:
    """
    Scrape today's duty pharmacies from the Ankara Eczacılar Odası.

    Returns a list of standardized dicts (name, address, district, phone,
    coordinates, duty_start, duty_end).
    """
    url = BASE_URL + timezone.localtime().strftime("%Y-%m-%d")
    response = requests.get(url, timeout=10, allow_redirects=False)
    if 300 <= response.status_code < 400:
        raise AnkaraScraperError(
            f"AEO endpoint {url} redirected with HTTP {response.status_code} "
            f"to {response.headers.get('Location')!r}; the endpoint has moved."
        )
    response.raise_for_status()

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise AnkaraScraperError(
            f"AEO endpoint {url} returned a non-JSON body."
        ) from exc
    if not isinstance(payload, dict) or payload.get("status") != "success":
        message = payload.get("message") if isinstance(payload, dict) else None
        raise AnkaraScraperError(
            f"AEO endpoint {url} did not return success: {message!r}"
        )
    html = payload.get("html")
    if not isinstance(html, str):
        raise AnkaraScraperError(f"AEO endpoint {url} returned no 'html' field.")

    soup = BeautifulSoup(html, "html.parser")
    duty_start, duty_end = _get_duty_times()
    pharmacies: list[dict[str, Any]] = []
    for box in soup.find_all("div", class_="inline-box"):
        if not isinstance(box, Tag):
            continue
        pharmacy = _parse_pharmacy(box, duty_start, duty_end)
        if pharmacy is not None:
            pharmacies.append(pharmacy)

    return pharmacies


if __name__ == "__main__":
    for pharmacy_data in get_ankara_data():
        print(pharmacy_data)
