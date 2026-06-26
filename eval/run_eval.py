#!/usr/bin/env python3
"""Evaluate produced baselines against gold labels.

For each eval/gold/<project>.json, loads projects/<project>/baseline.json and
compares field by field. Prints a per-project table and overall accuracy.

Classification gold labels (eval/gold/classifications.json) are a manual
reference for Scope Sentinel runs — not auto-graded here.

Usage:
    python eval/run_eval.py
"""
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "eval" / "gold"
PROJECTS_DIR = REPO_ROOT / "projects"


def unwrap(value):
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def get_path(data, dotted):
    node = data
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


# gold key -> (baseline path, comparison)
SCALAR_FIELDS = {
    "engagement_type": ("engagement_type", "unwrap"),
    "currency": ("commercials.currency", "raw"),
    "total_value": ("commercials.total_value", "unwrap"),
    "stated_monthly_fee": ("commercials.stated_monthly_fee", "unwrap"),
    "stated_term_total": ("commercials.stated_term_total", "unwrap"),
    "start_date": ("dates.start_date", "unwrap"),
    "end_date": ("dates.end_date", "unwrap"),
}

COUNT_FIELDS = {
    "milestones_count": "milestones",
    "scope_items_count": "scope_items",
    "deliverables_count": "deliverables",
    "assumptions_count": "assumptions",
    "exclusions_count": "exclusions",
}


def compare_project(gold_path):
    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)
    project_id = gold["project_id"]
    baseline_path = PROJECTS_DIR / project_id / "baseline.json"

    print(f"\n=== {project_id} ===")
    if not baseline_path.exists():
        print(f"  SKIP — no baseline.json yet (run sow-intake on this project first)")
        return None

    with open(baseline_path, encoding="utf-8") as f:
        baseline = json.load(f)

    passed, total = 0, 0

    def check(label, expected, actual):
        nonlocal passed, total
        total += 1
        ok = expected == actual
        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"  {mark}  {label}: expected {expected!r}, got {actual!r}")

    for gold_key, (path, mode) in SCALAR_FIELDS.items():
        if gold_key not in gold:
            continue
        actual = get_path(baseline, path)
        if mode == "unwrap":
            actual = unwrap(actual)
        check(gold_key, gold[gold_key], actual)

    for gold_key, list_key in COUNT_FIELDS.items():
        if gold_key not in gold:
            continue
        items = baseline.get(list_key) or []
        check(gold_key, gold[gold_key], len(items) if isinstance(items, list) else None)

    if "expected_not_found" in gold:
        found = set(get_path(baseline, "extraction_meta.fields_not_found") or [])
        for field in gold["expected_not_found"]:
            total += 1
            ok = field in found
            passed += ok
            print(f"  {'PASS' if ok else 'FAIL'}  NOT_FOUND declared: {field}")

    if "expected_risk_flags" in gold:
        flag_types = {f.get("type") for f in baseline.get("risk_flags", [])}
        for flag in gold["expected_risk_flags"]:
            total += 1
            ok = flag in flag_types
            passed += ok
            print(f"  {'PASS' if ok else 'FAIL'}  risk flag detected: {flag}")

    if "expected_cap_values" in gold:
        caps = get_path(baseline, "commercials.monthly_hours_cap")
        caps = sorted(caps) if isinstance(caps, list) else caps
        check("conflicting caps recorded (both values)", sorted(gold["expected_cap_values"]), caps)

    print(f"  -> {passed}/{total} fields correct ({100 * passed / total:.0f}%)")
    return passed, total


def main():
    gold_files = sorted(p for p in GOLD_DIR.glob("*.json") if p.name != "classifications.json")
    if not gold_files:
        sys.exit("No gold files found in eval/gold/")

    grand_passed, grand_total = 0, 0
    evaluated = 0
    for gold_path in gold_files:
        result = compare_project(gold_path)
        if result:
            grand_passed += result[0]
            grand_total += result[1]
            evaluated += 1

    if grand_total:
        print(f"\n=== OVERALL: {grand_passed}/{grand_total} ({100 * grand_passed / grand_total:.0f}%) across {evaluated} project(s) ===")
        print("Scope Sentinel classifications: compare manually against eval/gold/classifications.json")
    else:
        print("\nNo baselines to evaluate yet. Run sow-intake on the projects first.")


if __name__ == "__main__":
    main()
