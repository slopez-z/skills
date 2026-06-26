#!/usr/bin/env python3
"""Portfolio status: one-screen deterministic view across all projects.

Reads every projects/<id>/baseline.json and scope-changelog.jsonl and prints
a portfolio table plus aggregate signals. No LLM involved.

This is the v0 seed of the Delivery Health Radar (roadmap): the same
aggregation, scheduled and trended over time, becomes the delivery
intelligence layer.

Usage:
    python scripts/portfolio_status.py
"""
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"


def unwrap(value):
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def load_changelog(project_dir: pathlib.Path):
    log_path = project_dir / "scope-changelog.jsonl"
    if not log_path.exists():
        return []
    events = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def main():
    rows = []
    total_events = []

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        baseline_path = project_dir / "baseline.json"
        if not baseline_path.exists():
            rows.append({
                "project": project_dir.name, "type": "—", "end_date": "—",
                "risks": "—", "not_found": "—", "crs": "—",
                "note": "PENDING INTAKE",
            })
            continue

        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)

        flags = baseline.get("risk_flags", [])
        high = sum(1 for f_ in flags if f_.get("severity") == "high")
        not_found = baseline.get("extraction_meta", {}).get("fields_not_found", [])
        events = load_changelog(project_dir)
        total_events.extend(events)
        approved = sum(1 for e in events if e.get("decision") == "approved")
        rejected = sum(1 for e in events if e.get("decision") == "rejected")

        rows.append({
            "project": baseline.get("project_id", project_dir.name),
            "type": str(unwrap(baseline.get("engagement_type", "?"))),
            "end_date": str(unwrap((baseline.get("dates") or {}).get("end_date", "?"))),
            "risks": f"{len(flags)} ({high} high)" if flags else "0",
            "not_found": str(len(not_found)),
            "crs": f"{approved} appr / {rejected} rej" if events else "0",
            "note": "",
        })

    columns = [
        ("PROJECT", "project", 38),
        ("TYPE", "type", 20),
        ("END DATE", "end_date", 11),
        ("RISK FLAGS", "risks", 11),
        ("NOT_FOUND", "not_found", 10),
        ("CR ACTIVITY", "crs", 16),
        ("", "note", 15),
    ]
    header = "  ".join(name.ljust(width) for name, _, width in columns)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row[key]).ljust(width) for _, key, width in columns))

    print()
    intaken = [r for r in rows if r["note"] != "PENDING INTAKE"]
    print(f"Portfolio: {len(rows)} project(s), {len(intaken)} with baseline, "
          f"{len(total_events)} scope decision(s) logged.")

    if total_events:
        by_project = {}
        for event in total_events:
            by_project.setdefault(event.get("project_id", "?"), []).append(event)
        most_active = max(by_project.items(), key=lambda kv: len(kv[1]))
        out_of_scope = sum(1 for e in total_events if e.get("classification") == "out_of_scope")
        print(f"Signals: most scope activity in '{most_active[0]}' "
              f"({len(most_active[1])} decision(s)); "
              f"{out_of_scope} out-of-scope request(s) portfolio-wide.")
        print("Roadmap: scheduled, this aggregation trended over time = Delivery Health Radar.")


if __name__ == "__main__":
    main()
