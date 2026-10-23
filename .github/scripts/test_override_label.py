"""Unit tests for override_label.py, run by the gate's test-removal job.

The issue events come from a real response: ``gh api --paginate --slurp
repos/gidorah/PharmacyOnDuty/issues/142/events``, recorded on 2026-10-23. It
holds three ``labeled`` events by gidorah. The tests rename those labels or
append events to build each case. The webhook payload is trimmed to the
fields the script reads, in the shape GitHub documents for ``pull_request``
``labeled`` events.

Run with: python3 -I -m unittest discover -s .github/scripts -p "test_*.py"
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from override_label import APPROVER, LABEL, decide, flatten_events

TESTDATA = Path(__file__).parent / "testdata"
HEAD = "5c03eec9cffa8a3a76efab872c15b8c6440bfc9f"


def recorded_events() -> list[dict[str, Any]]:
    with open(TESTDATA / "issue_142_events.json", encoding="utf-8") as handle:
        return flatten_events(json.load(handle))


def labeled_payload() -> dict[str, Any]:
    with open(
        TESTDATA / "pull_request_labeled_payload.json", encoding="utf-8"
    ) as handle:
        payload: dict[str, Any] = json.load(handle)
    return payload


def events_with_approval() -> list[dict[str, Any]]:
    """The recorded events, with gidorah's latest label renamed to ours."""
    events = recorded_events()
    latest = max(events, key=lambda e: e["created_at"])
    latest["label"]["name"] = LABEL
    return events


def later_event(events: list[dict[str, Any]], kind: str, login: str) -> dict[str, Any]:
    """Copy the approval event as a later event of another kind or actor."""
    approval = max(events, key=lambda e: e["created_at"])
    event = copy.deepcopy(approval)
    event["event"] = kind
    event["actor"]["login"] = login
    event["created_at"] = "2026-10-23T18:00:00Z"
    event["id"] = approval["id"] + 1
    return event


class TestDecide(unittest.TestCase):
    def test_recorded_events_have_the_expected_shape(self) -> None:
        events = recorded_events()
        self.assertEqual(len(events), 3)
        for event in events:
            self.assertEqual(event["event"], "labeled")
            self.assertEqual(event["actor"]["login"], APPROVER)
            self.assertIn("name", event["label"])

    def test_allows_when_gidorah_added_the_label_on_this_commit(self) -> None:
        decision = decide(
            "pull_request", labeled_payload(), events_with_approval(), HEAD
        )
        self.assertTrue(decision.allowed, decision.reason)

    def test_denies_when_events_show_no_label_change(self) -> None:
        decision = decide("pull_request", labeled_payload(), recorded_events(), HEAD)
        self.assertFalse(decision.allowed)

    def test_denies_when_label_was_removed_later(self) -> None:
        events = events_with_approval()
        events.append(later_event(events, "unlabeled", APPROVER))
        decision = decide("pull_request", labeled_payload(), events, HEAD)
        self.assertFalse(decision.allowed)
        self.assertIn("removed", decision.reason)

    def test_allows_when_gidorah_removed_and_added_it_again(self) -> None:
        events = events_with_approval()
        removal = later_event(events, "unlabeled", APPROVER)
        readd = copy.deepcopy(removal)
        readd["event"] = "labeled"
        readd["created_at"] = "2026-10-23T18:05:00Z"
        readd["id"] = removal["id"] + 1
        events += [removal, readd]
        decision = decide("pull_request", labeled_payload(), events, HEAD)
        self.assertTrue(decision.allowed, decision.reason)

    def test_denies_when_a_bot_added_the_label_last(self) -> None:
        events = events_with_approval()
        events.append(later_event(events, "labeled", "github-actions[bot]"))
        decision = decide("pull_request", labeled_payload(), events, HEAD)
        self.assertFalse(decision.allowed)

    def test_denies_when_the_sender_is_not_gidorah(self) -> None:
        payload = labeled_payload()
        payload["sender"]["login"] = "github-actions[bot]"
        decision = decide("pull_request", payload, events_with_approval(), HEAD)
        self.assertFalse(decision.allowed)

    def test_denies_when_the_run_checks_another_commit(self) -> None:
        decision = decide(
            "pull_request", labeled_payload(), events_with_approval(), "0" * 40
        )
        self.assertFalse(decision.allowed)

    def test_denies_for_other_labels(self) -> None:
        payload = labeled_payload()
        payload["label"]["name"] = "needs-human"
        decision = decide("pull_request", payload, events_with_approval(), HEAD)
        self.assertFalse(decision.allowed)

    def test_denies_for_new_commits_and_other_actions(self) -> None:
        for action in ("synchronize", "opened", "reopened", "unlabeled"):
            payload = labeled_payload()
            payload["action"] = action
            decision = decide("pull_request", payload, events_with_approval(), HEAD)
            self.assertFalse(decision.allowed, action)

    def test_denies_for_dispatch_and_push_runs(self) -> None:
        for event_name in ("workflow_dispatch", "push"):
            decision = decide(event_name, {}, events_with_approval(), HEAD)
            self.assertFalse(decision.allowed, event_name)

    def test_flatten_accepts_pages_from_slurp(self) -> None:
        events = recorded_events()
        self.assertEqual(flatten_events([events[:2], events[2:]]), events)


if __name__ == "__main__":
    unittest.main()
