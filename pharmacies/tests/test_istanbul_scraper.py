import logging
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from requests.cookies import RequestsCookieJar
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    ReadTimeout,
    RequestException,
    Timeout,
)

from pharmacies.utils.istanbul_edevlet_scraper import (
    MAP_WORKERS,
    get_istanbul_data,
    save_to_csv,
)

MODULE = "pharmacies.utils.istanbul_edevlet_scraper"
FIXTURES = Path(__file__).parent / "fixtures"
DUTY_START = datetime(2025, 12, 16, 15, 30, tzinfo=UTC)
DUTY_END = datetime(2025, 12, 17, 6, 0, tzinfo=UTC)
NOW = datetime(2026, 10, 31, 20, 30, tzinfo=UTC)  # 23:30 on 31 Oct in Istanbul


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _response(text: str = "", error: Exception | None = None) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status.side_effect = error
    return response


def _map_page(url: str, **_: Any) -> MagicMock:
    name = "edevlet_map_1.html" if url.endswith("index=1") else "edevlet_map_0.html"
    return _response(_fixture(name))


@pytest.fixture(autouse=True)
def _fixed_duty_window() -> Iterator[None]:
    """Keep scraper tests off the database."""
    with patch(
        f"{MODULE}.get_duty_window", return_value=(DUTY_START, DUTY_END)
    ) as window:
        window.reset_mock()
        yield


@pytest.fixture(autouse=True)
def _fixed_now() -> Iterator[None]:
    with patch(f"{MODULE}.timezone.now", return_value=NOW):
        yield


@pytest.fixture
def session() -> Iterator[MagicMock]:
    """A session that serves the recorded form and result pages."""
    with patch(f"{MODULE}.requests.Session") as session_class:
        instance = session_class.return_value
        jar = RequestsCookieJar()
        jar.set("TURKIYESESSIONID", "abc")
        instance.cookies = jar
        instance.get.return_value = _response(_fixture("edevlet_form.html"))
        instance.post.return_value = _response(_fixture("edevlet_result.html"))
        yield instance


@pytest.fixture
def map_get() -> Iterator[MagicMock]:
    with patch(f"{MODULE}.requests.get", side_effect=_map_page) as mock_get:
        yield mock_get


def test_get_istanbul_data_parses_recorded_result(
    session: MagicMock, map_get: MagicMock
) -> None:
    data = get_istanbul_data()

    assert len(data) == 126
    assert data[0] == {
        "district": "Adalar",
        "name": "BURGAZADA",
        "address": "ÇINARLIK SOKAK NO:5/A BURGAZADA",
        "phone": "02163812112",
        "coordinates": {"lat": 40.8799133300781, "lng": 29.0689487457275},
        "duty_start": DUTY_START,
        "duty_end": DUTY_END,
    }
    assert data[1]["name"] == "DENIZ"
    assert data[1]["phone"] == "02163815181"
    assert data[2]["name"] == "HEYBELİADA"
    assert data[2]["district"] == "Adalar"
    assert map_get.call_count == 126
    first_url = map_get.call_args_list[0].args[0]
    assert first_url == (
        "https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama"
        "?harita=Goster&index=0"
    )
    assert map_get.call_args_list[0].kwargs["cookies"] == {"TURKIYESESSIONID": "abc"}
    assert map_get.call_args_list[0].kwargs["timeout"] == 10


def test_get_istanbul_data_posts_istanbul_query_with_token(
    session: MagicMock, map_get: MagicMock
) -> None:
    get_istanbul_data()

    form_page = _fixture("edevlet_form.html")
    token = form_page.split('name="token" value="')[1].split('"')[0]
    assert token
    session.get.assert_called_once()
    assert session.get.call_args.args[0] == (
        "https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama"
    )
    assert session.get.call_args.kwargs["timeout"] == 10
    session.post.assert_called_once()
    assert session.post.call_args.args[0] == (
        "https://www.turkiye.gov.tr/saglik-titck-nobetci-eczane-sorgulama?submit"
    )
    assert session.post.call_args.kwargs["timeout"] == 10
    form = session.post.call_args.kwargs["data"]
    assert form["ilkod-address-il"] == "34"
    assert form["token"] == token


@pytest.mark.parametrize(
    ("now", "duty_day"),
    [
        (datetime(2026, 10, 31, 5, 59, tzinfo=UTC), "30/10/2026"),  # 08:59 TRT
        (datetime(2026, 10, 31, 6, 0, tzinfo=UTC), "31/10/2026"),  # 09:00 TRT
        (datetime(2026, 10, 31, 20, 30, tzinfo=UTC), "31/10/2026"),  # 23:30 TRT
        (datetime(2026, 10, 31, 22, 30, tzinfo=UTC), "31/10/2026"),  # 01:30 TRT, 1 Nov
    ],
)
def test_get_istanbul_data_posts_the_duty_day_on_duty_now(
    session: MagicMock, map_get: MagicMock, now: datetime, duty_day: str
) -> None:
    with patch(f"{MODULE}.timezone.now", return_value=now):
        get_istanbul_data()

    assert session.post.call_args.kwargs["data"]["nobetTarihi"] == duty_day


def test_get_istanbul_data_skips_pharmacy_without_coordinates(
    session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            return _response("<html>no map here</html>")
        return _map_page(url)

    with (
        patch(f"{MODULE}.requests.get", side_effect=pages),
        caplog.at_level(logging.WARNING, logger=MODULE),
    ):
        data = get_istanbul_data()

    assert len(data) == 125
    assert "DENIZ" not in [p["name"] for p in data]
    assert data[1]["name"] == "HEYBELİADA"
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == ["Unable to get coordinates for DENIZ"]


def test_get_istanbul_data_skips_pharmacy_on_map_http_error(
    session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            return _response(error=HTTPError("500 Server Error"))
        return _map_page(url)

    with (
        patch(f"{MODULE}.requests.get", side_effect=pages),
        caplog.at_level(logging.WARNING, logger=MODULE),
    ):
        data = get_istanbul_data()

    assert len(data) == 125
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == ["Unable to get coordinates for DENIZ"]


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(
            "var latti = parseFloat(NaN);var longi = parseFloat(29.0);", id="nan"
        ),
        pytest.param(
            "var latti = parseFloat(95.0);var longi = parseFloat(29.0);", id="lat-range"
        ),
        pytest.param(
            "var latti = parseFloat(41.0);var longi = parseFloat(200.0);",
            id="lng-range",
        ),
    ],
)
def test_get_istanbul_data_skips_out_of_range_coordinates(
    session: MagicMock, page: str
) -> None:
    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            return _response(page)
        return _map_page(url)

    with patch(f"{MODULE}.requests.get", side_effect=pages):
        data = get_istanbul_data()

    assert len(data) == 125
    assert "DENIZ" not in [p["name"] for p in data]


def test_get_istanbul_data_rejected_form_raises(
    session: MagicMock, map_get: MagicMock
) -> None:
    session.post.return_value = _response(_fixture("edevlet_rejected.html"))

    with pytest.raises(RequestException):
        get_istanbul_data()

    map_get.assert_not_called()


@pytest.mark.parametrize(
    "page",
    [
        pytest.param("<html><body>maintenance</body></html>", id="no-table"),
        pytest.param(
            '<table id="searchTable"><thead><tr><th>İlçe</th></tr></thead>'
            "<tbody></tbody></table>",
            id="zero-rows",
        ),
    ],
)
def test_get_istanbul_data_without_rows_raises(
    session: MagicMock, map_get: MagicMock, page: str
) -> None:
    session.post.return_value = _response(page)

    with pytest.raises(RequestException):
        get_istanbul_data()

    map_get.assert_not_called()


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(ConnectionError("down"), id="connection-error"),
        pytest.param(Timeout("timed out"), id="timeout"),
        pytest.param(HTTPError("503 Server Error"), id="http-error"),
    ],
)
def test_get_istanbul_data_form_or_post_failure_raises(
    session: MagicMock, map_get: MagicMock, method: str, failure: Exception
) -> None:
    if isinstance(failure, HTTPError):
        getattr(session, method).return_value = _response(error=failure)
    else:
        getattr(session, method).side_effect = failure

    with pytest.raises(RequestException):
        get_istanbul_data()

    map_get.assert_not_called()


def test_get_istanbul_data_missing_token_raises(
    session: MagicMock, map_get: MagicMock
) -> None:
    session.get.return_value = _response("<form id='mainForm'></form>")

    with pytest.raises(RequestException, match="token"):
        get_istanbul_data()

    session.post.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [ConnectionError("down"), Timeout("timed out")],
    ids=["connection-error", "timeout"],
)
def test_get_istanbul_data_map_host_gone_stops_at_once(
    session: MagicMock, failure: Exception
) -> None:
    with (
        patch(f"{MODULE}.requests.get", side_effect=failure) as mock_get,
        pytest.raises(RequestException, match="unreachable") as excinfo,
    ):
        get_istanbul_data()

    assert excinfo.value.__cause__ is not None
    assert mock_get.call_count <= 4 * MAP_WORKERS


def test_get_istanbul_data_map_page_retried_after_read_timeout(
    session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    attempts: list[str] = []

    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            attempts.append(url)
            if len(attempts) == 1:
                raise ReadTimeout("read timed out")
        return _map_page(url)

    with (
        patch(f"{MODULE}.requests.get", side_effect=pages),
        caplog.at_level(logging.WARNING, logger=MODULE),
    ):
        data = get_istanbul_data()

    assert len(data) == 126
    assert len(attempts) == 2
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_get_istanbul_data_map_page_failing_twice_is_skipped(
    session: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            raise ConnectionError("Failure when receiving data from the peer")
        return _map_page(url)

    with (
        patch(f"{MODULE}.requests.get", side_effect=pages),
        caplog.at_level(logging.WARNING, logger=MODULE),
    ):
        data = get_istanbul_data()

    assert len(data) == 125
    assert "DENIZ" not in [p["name"] for p in data]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == ["Unable to get coordinates for DENIZ"]


def test_get_istanbul_data_map_http_error_is_retried(session: MagicMock) -> None:
    calls: list[str] = []

    def pages(url: str, **_: Any) -> MagicMock:
        if url.endswith("index=1"):
            calls.append(url)
            if len(calls) == 1:
                return _response(error=HTTPError("503 Server Error"))
        return _map_page(url)

    with patch(f"{MODULE}.requests.get", side_effect=pages):
        data = get_istanbul_data()

    assert len(data) == 126
    assert len(calls) == 2


def test_save_to_csv() -> None:
    data = [{"name": "Test", "phone": "123"}]
    filename = "test_pharmacies.csv"
    save_to_csv(data, filename)

    assert os.path.exists(filename)
    with open(filename) as f:
        content = f.read()
        assert "name,phone" in content
        assert "Test,123" in content

    os.remove(filename)


def test_save_to_csv_empty() -> None:
    data: list[dict[str, str]] = []
    filename = "test_pharmacies_empty.csv"
    save_to_csv(data, filename)

    assert os.path.exists(filename)
    os.remove(filename)
