"""Decide whether Onur approved removing tests in this gate run.

The test-removal check accepts removed or skipped tests only when this script
says the run carries Onur's approval. Approval means all of the following:

1. The run was started by a ``pull_request`` event with action ``labeled``
   for the ``allow-test-removal`` label. Every other event ignores the label:
   new commits (``synchronize``), other label changes, reopening, and
   ``workflow_dispatch`` runs from the pipeline. Pushes made with the built-in
   token start no workflow, so the job that removes the label on new commits
   cannot be relied on, and only a ``labeled`` event pins the commit Onur saw.
2. The event's sender is ``gidorah``.
3. The commit under test is the head commit in that event's payload.
4. In the pull request's issue events, the latest ``labeled`` or ``unlabeled``
   event for the label is a ``labeled`` event by ``gidorah``. So the label is
   still on the pull request, and nobody removed and re-added it since.

Usage, in the gate's test-removal job:
    python3 override_label.py --event-name NAME --event-path PAYLOAD.json
        --issue-events EVENTS.json --head SHA

``EVENTS.json`` is the output of ``gh api --paginate --slurp`` on
``repos/{owner}/{repo}/issues/{number}/events``. The script prints its reason
and writes ``allowed=true`` or ``allowed=false`` to ``$GITHUB_OUTPUT``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any

LABEL = "allow-test-removal"
APPROVER = "gidorah"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def flatten_events(data: Any) -> list[dict[str, Any]]:
    """Accept one page of events, or the list of pages from ``--slurp``."""
    events: list[dict[str, Any]] = []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        for item in data:
            events.extend(flatten_events(item))
    return events


def decide(
    event_name: str,
    payload: dict[str, Any],
    issue_events: list[dict[str, Any]],
    head_sha: str,
) -> Decision:
    if event_name != "pull_request":
        return Decision(
            False, f"This run was started by {event_name}, which ignores the label."
        )
    action = payload.get("action")
    label_name = (payload.get("label") or {}).get("name")
    if action != "labeled" or label_name != LABEL:
        return Decision(
            False,
            f"This run was started by pull_request {action}, not by adding "
            f"the {LABEL} label, so it ignores the label.",
        )

    sender = (payload.get("sender") or {}).get("login")
    if sender != APPROVER:
        return Decision(False, f"{sender} added the label; only {APPROVER} can.")

    payload_head = ((payload.get("pull_request") or {}).get("head") or {}).get("sha")
    if payload_head != head_sha:
        return Decision(
            False,
            f"The label was added on {payload_head}, but this run checks {head_sha}.",
        )

    label_changes = [
        event
        for event in issue_events
        if event.get("event") in ("labeled", "unlabeled")
        and (event.get("label") or {}).get("name") == LABEL
    ]
    if not label_changes:
        return Decision(False, "The issue events show no change to the label.")
    latest = max(label_changes, key=lambda e: (e.get("created_at", ""), e.get("id", 0)))
    actor = (latest.get("actor") or {}).get("login")
    if latest.get("event") != "labeled":
        return Decision(False, f"{actor} removed the label after it was added.")
    if actor != APPROVER:
        return Decision(False, f"{actor} added the label last; only {APPROVER} can.")

    return Decision(
        True,
        f"{APPROVER} added the {LABEL} label on {head_sha[:12]} "
        f"at {latest.get('created_at')}.",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decide whether this gate run carries approval to remove tests."
    )
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--issue-events", help="JSON file from gh api --slurp.")
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    with open(args.event_path, encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    issue_events: list[dict[str, Any]] = []
    if args.issue_events:
        with open(args.issue_events, encoding="utf-8") as handle:
            issue_events = flatten_events(json.load(handle))

    decision = decide(args.event_name, payload, issue_events, args.head)
    print(decision.reason)
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"allowed={'true' if decision.allowed else 'false'}\n")
            output.write(f"reason={decision.reason}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
