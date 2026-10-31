"""
Scraper for the Health Ministry's e-Devlet service "TİTCK Nöbetçi Eczane Sorgulama".

Reads the Istanbul duty list now on duty from
https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama (no login): one GET
for the form's session cookie and token, one city-wide POST, then one map page per
pharmacy for its coordinates.
"""

import csv
import logging
import math
import re
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from django.utils import timezone

from pharmacies.models import ISTANBUL_TZ
from pharmacies.utils.duty_window import get_duty_window

SERVICE_URL = "https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama"
SUBMIT_URL = f"{SERVICE_URL}?submit"
ISTANBUL_PLATE_CODE = "34"
REQUEST_TIMEOUT = 10
MAP_WORKERS = 4
# A duty day D runs from 09:00 on D to 09:00 on D+1 (Istanbul time), so before 09:00
# the list on duty is the previous day's.
DUTY_DAY_HANDOVER = timedelta(hours=9)

_LATITUDE = re.compile(r"var\s+latti\s*=\s*parseFloat\(\s*([^)\s]+)\s*\)")
_LONGITUDE = re.compile(r"var\s+longi\s*=\s*parseFloat\(\s*([^)\s]+)\s*\)")

logger = logging.getLogger(__name__)


class _MapConnectionError(Exception):
    """A map page could not be reached (connection error or timeout) after its retry."""


def _fetch_form_and_result(duty_day: str) -> tuple[BeautifulSoup, dict[str, str]]:
    """GET the form, POST the Istanbul query, return the result page and cookies."""
    session = requests.Session()
    try:
        form_response = session.get(SERVICE_URL, timeout=REQUEST_TIMEOUT)
        form_response.raise_for_status()
        form_soup = BeautifulSoup(form_response.text, "html.parser")
        token_input = form_soup.select_one("form#mainForm input[name=token]")
        token = token_input.get("value") if token_input else None
        if not token or not isinstance(token, str):
            raise requests.exceptions.RequestException(
                "e-Devlet form has no token input"
            )
        response = session.post(
            SUBMIT_URL,
            data={
                "ilkod-address-il": ISTANBUL_PLATE_CODE,
                "ilkod-address-il-text": "İSTANBUL",
                "ilkod-full": "",
                "ilkod": "",
                "nobetTarihi": duty_day,
                "token": token,
                "btn": "Sorgula",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if str(e).startswith("e-Devlet form has no token"):
            raise
        raise requests.exceptions.RequestException(
            f"e-Devlet Istanbul request failed: {e}"
        ) from e
    cookies: dict[str, str] = session.cookies.get_dict()
    return BeautifulSoup(response.text, "html.parser"), cookies


def _parse_coordinate(
    pattern: re.Pattern[str], page: str, limit: float
) -> float | None:
    match = pattern.search(page)
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if not math.isfinite(value) or abs(value) > limit:
        return None
    return value


def _get_map_page(url: str, cookies: dict[str, str]) -> str:
    response = requests.get(url, cookies=cookies, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def _fetch_coordinates(url: str, cookies: dict[str, str]) -> dict[str, float] | None:
    """
    Coordinates from a map page, fetched with one retry on any request error.

    None when the page has no valid coordinates or still errors out with an HTTP
    error after the retry. Raises ``_MapConnectionError`` when the retry also fails
    with a connection error or timeout.
    """
    try:
        try:
            page = _get_map_page(url, cookies)
        except requests.exceptions.RequestException:
            page = _get_map_page(url, cookies)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise _MapConnectionError(str(e)) from e
    except requests.exceptions.RequestException:
        return None
    lat = _parse_coordinate(_LATITUDE, page, 90)
    lng = _parse_coordinate(_LONGITUDE, page, 180)
    if lat is None or lng is None:
        return None
    return {"lat": lat, "lng": lng}


def _first_text(cell: Tag) -> str:
    """The cell's own leading text; the source leaves some cells unclosed."""
    text = cell.find(string=True)
    return str(text) if isinstance(text, NavigableString) else ""


def get_istanbul_data() -> list[dict[str, Any]]:
    """
    Scrape the Istanbul pharmacies on duty now from the e-Devlet service.

    Fetches the form for its session cookie and token, posts one city-wide query
    (``ilkod-address-il=34`` and the duty day on duty now as ``nobetTarihi``), parses
    ``table#searchTable`` and reads each pharmacy's coordinates from its map page,
    four pages at a time. The duty window is ``get_duty_window("istanbul")``, the
    source's own start and end times are ignored.

    A map page that fails with a request error is retried once. A pharmacy whose
    coordinates can't be got (still failing, or no valid coordinates) is skipped
    with a warning. A scrape that gets no list (request error, form returned
    again, no table or no rows), or where ``MAP_WORKERS`` pharmacies in a row fail
    with a connection error or timeout, raises ``requests.exceptions.RequestException``
    so the caller treats it as an upstream failure rather than an empty result.
    """
    duty_day = (timezone.now().astimezone(ISTANBUL_TZ) - DUTY_DAY_HANDOVER).strftime(
        "%d/%m/%Y"
    )
    soup, cookies = _fetch_form_and_result(duty_day)

    if soup.select_one("table#searchTable") is None:
        raise requests.exceptions.RequestException(
            "e-Devlet returned no result table for Istanbul"
        )
    rows = soup.select("table#searchTable tbody tr")
    if not rows:
        raise requests.exceptions.RequestException(
            "e-Devlet result table for Istanbul has no rows"
        )

    entries: list[dict[str, Any]] = []
    map_urls: list[str | None] = []
    for row in rows:
        cells = row.find_all("td")
        link = row.select_one("a[href*='harita=Goster']")
        href = link.get("href") if link else None
        if len(cells) < 4:
            continue
        entries.append(
            {
                "district": cells[0].get_text().strip(),
                "name": cells[1].get_text().strip(),
                "address": " ".join(cells[2].get_text().split()),
                "phone": re.sub(r"\D", "", _first_text(cells[3])),
            }
        )
        map_urls.append(urljoin(SERVICE_URL, href) if isinstance(href, str) else None)

    # Submit in batches of MAP_WORKERS and count connection-level failures in table
    # order: MAP_WORKERS in a row (only a success resets the count) mean the host is
    # gone, so no further batch is requested.
    coordinates: list[dict[str, float] | None] = []
    consecutive_failures = 0
    with ThreadPoolExecutor(max_workers=MAP_WORKERS) as executor:
        for start in range(0, len(map_urls), MAP_WORKERS):
            batch: list[Future[dict[str, float] | None] | None] = [
                executor.submit(_fetch_coordinates, url, cookies) if url else None
                for url in map_urls[start : start + MAP_WORKERS]
            ]
            for future in batch:
                coords = None
                if future is not None:
                    try:
                        coords = future.result()
                    except _MapConnectionError as e:
                        consecutive_failures += 1
                        if consecutive_failures >= MAP_WORKERS:
                            executor.shutdown(wait=False, cancel_futures=True)
                            raise requests.exceptions.RequestException(
                                f"e-Devlet map pages unreachable: {e}"
                            ) from e
                if coords is not None:
                    consecutive_failures = 0
                coordinates.append(coords)

    duty_start, duty_end = get_duty_window("istanbul")
    pharmacies: list[dict[str, Any]] = []
    for entry, coords in zip(entries, coordinates, strict=True):
        if coords is None:
            logger.warning("Unable to get coordinates for %s", entry["name"])
            continue
        pharmacies.append(
            {
                **entry,
                "coordinates": coords,
                "duty_start": duty_start,
                "duty_end": duty_end,
            }
        )
    return pharmacies


def save_to_csv(data: list[dict[str, Any]], filename: str = "pharmacies.csv") -> None:
    """Helper to save scraped data to CSV for debugging."""
    keys = data[0].keys() if data else []
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)


if __name__ == "__main__":
    pharmacies = get_istanbul_data()
    save_to_csv(pharmacies)
    print(f"Collected {len(pharmacies)} pharmacy records")
