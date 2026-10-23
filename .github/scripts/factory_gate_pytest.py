"""Pytest plugin that the factory gate loads with ``-p factory_gate_pytest``.

It changes two things for the gate's test run only. Local ``pytest`` runs are
unaffected.

1. Tests get no outbound network. Python code may connect only to loopback
   addresses, where the PostGIS and Redis service containers listen. Any other
   connection or DNS lookup raises ``NetworkBlockedError``. The plugin also
   records the attempt and fails the test, so a test still fails when the code
   under test catches the error.
2. Celery runs tasks inline. ``task.delay()`` executes in the test process and
   raises the task's errors there, so no worker is needed.

The guard covers Python sockets. C libraries that open their own sockets, such
as libpq inside psycopg2, bypass it; the gate points them only at localhost.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Generator
from typing import Any

import pytest

LOOPBACK_NAMES = frozenset({"localhost", "localhost.localdomain", "ip6-localhost"})
INET_FAMILIES = (socket.AF_INET, socket.AF_INET6)


class NetworkBlockedError(RuntimeError):
    """Raised when a test tries to reach a host outside this machine."""


_attempts: list[tuple[str, str]] = []
_current_test = "<collection>"
_reported = 0
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo


def _is_loopback(host: object) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    if not isinstance(host, str):
        return False
    if host.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def _block(host: object, port: object) -> None:
    target = f"{host!s}:{port!s}"
    _attempts.append((_current_test, target))
    raise NetworkBlockedError(
        f"The factory gate blocks outbound network in tests: {target}. "
        "Mock the call or use a saved response."
    )


def _guarded_connect(self: socket.socket, address: Any) -> None:
    if self.family in INET_FAMILIES and not _is_loopback(address[0]):
        _block(address[0], address[1])
    _original_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    if self.family in INET_FAMILIES and not _is_loopback(address[0]):
        _block(address[0], address[1])
    return _original_connect_ex(self, address)


def _guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
    if host is not None and not _is_loopback(host):
        _block(host, port)
    return _original_getaddrinfo(host, port, *args, **kwargs)


def pytest_configure(config: pytest.Config) -> None:
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_sessionstart(session: pytest.Session) -> None:
    from PharmacyOnDuty.celery import app

    app.conf.update(task_always_eager=True, task_eager_propagates=True)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Generator[None, object, object]:
    global _current_test
    _current_test = item.nodeid
    try:
        return (yield)
    finally:
        _current_test = "<between tests>"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    global _reported
    report = yield
    blocked = [target for test, target in _attempts[_reported:] if test == item.nodeid]
    _reported = len(_attempts)
    # A test that already failed shows the NetworkBlockedError itself. This
    # catches tests that pass because the code under test swallowed the error.
    if blocked and report.passed:
        report.outcome = "failed"
        report.longrepr = (
            f"The test tried to reach the network during {report.when}, which "
            "the factory gate blocks: " + ", ".join(sorted(set(blocked)))
        )
    return report


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    outside_tests = [target for test, target in _attempts if test.startswith("<")]
    if outside_tests:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        print(
            "\nfactory gate: network access outside a test (during collection "
            "or between tests): " + ", ".join(sorted(set(outside_tests)))
        )


def pytest_terminal_summary(terminalreporter: Any) -> None:
    if _attempts:
        terminalreporter.section("factory gate: blocked network access")
        for test, target in _attempts:
            terminalreporter.write_line(f"{test} -> {target}")
