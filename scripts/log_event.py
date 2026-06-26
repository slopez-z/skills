#!/usr/bin/env python3
"""Append an approved/rejected scope decision to the project's
scope-changelog.jsonl. Append-only, one JSON object per line.

This changelog is the seed of the portfolio loop: aggregated across projects
it shows which accounts erode scope and which deliverable types generate
creep (Delivery Health Radar roadmap).

Usage:
    python scripts/log_event.py projects/<project>/ --json '{"request_source": "...",
        "classification": "...", "cited_section": "...", "size": "...",
        "hours_range": [16, 40], "cost_range_usd": [1680, 4200],
        "decision": "approved", "approver": "Name"}'
"""
import argparse
import datetime
import json
import pathlib
import sys

REQUIRED_FIELDS = ["request_source", "classification", "decision", "approver"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--json", required=True, help="Event payload as a JSON string")
    args = parser.parse_args()

    try:
        event = json.loads(args.json)
    except json.JSONDecodeError as exc:
        sys.exit(f"Invalid JSON payload: {exc}")

    missing = [field for field in REQUIRED_FIELDS if field not in event]
    if missing:
        sys.exit(f"Missing required fields: {missing}")

    if event["decision"] not in ("approved", "rejected"):
        sys.exit("decision must be 'approved' or 'rejected' — pending items are not logged")

    project_dir = pathlib.Path(args.project_dir)
    event["project_id"] = project_dir.name
    event["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    changelog = project_dir / "scope-changelog.jsonl"
    with open(changelog, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"Logged to {changelog}")


if __name__ == "__main__":
    main()
