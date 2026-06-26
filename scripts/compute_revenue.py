#!/usr/bin/env python3
"""Deterministic commercial math for a project baseline.

The LLM extracts numbers (with citations); this script does ALL arithmetic:
payment schedule checks, T&M run-rates, staff-aug totals. The model never
computes money. If the baseline contains contradictions or NOT_FOUND values,
this script surfaces them and refuses to guess.

Usage:
    python scripts/compute_revenue.py projects/<project>/

Reads:  <project>/baseline.json, rate card (project override or config default)
Prints: commercial summary + FLAGS block (paste verbatim into the brief).
"""
import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def unwrap(value):
    """Return .value for cited objects, else the raw value."""
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def load_rate_card(project_dir: pathlib.Path):
    local = project_dir / "rate-card.json"
    path = local if local.exists() else REPO_ROOT / "config" / "rate-card.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def money(amount, currency="USD"):
    return f"{currency} {amount:,.0f}"


def fixed_price(commercials, flags):
    currency = commercials.get("currency", "USD")
    total = unwrap(commercials.get("total_value"))
    schedule = commercials.get("payment_schedule", [])

    print(f"Total fixed price: {money(total, currency) if isinstance(total, (int, float)) else total}")
    if not isinstance(total, (int, float)):
        flags.append("total_value is missing or NOT_FOUND — cannot verify payment schedule")

    if schedule:
        print("Payment schedule:")
        sched_sum = 0.0
        for item in schedule:
            amount = item.get("amount", 0) or 0
            sched_sum += amount
            print(f"  {item.get('percent', '?')}% on {item.get('trigger', '?')}: {money(amount, currency)}")
        sched_sum = round(sched_sum, 2)
        if isinstance(total, (int, float)):
            if sched_sum == round(total, 2):
                print(f"Schedule check: OK — milestones sum to {money(sched_sum, currency)}")
            else:
                flags.append(
                    f"payment schedule sums to {money(sched_sum, currency)} but SOW total is "
                    f"{money(total, currency)} — discrepancy requires human resolution"
                )
    else:
        flags.append("no payment schedule found in baseline")


def time_and_materials(commercials, rate_card, flags):
    currency = commercials.get("currency", "USD")
    rates = commercials.get("rates", {})
    if rates:
        print("Hourly rates (as stated in SOW):")
        for role, rate in rates.items():
            print(f"  {role}: {money(rate, currency)}/h")

    caps = commercials.get("monthly_hours_cap", "NOT_FOUND")
    cap_values = caps if isinstance(caps, list) else [caps]
    cap_values = sorted({c for c in cap_values if isinstance(c, (int, float))})

    blended = rate_card["blended_hourly_rate"]
    if len(cap_values) > 1:
        flags.append(
            f"SOW states CONFLICTING monthly hour caps: {cap_values} — "
            "human resolution required before any commitment; scenarios below are illustrative only"
        )
    if not cap_values:
        flags.append("monthly hours cap is NOT_FOUND — run-rate cannot be computed")

    for cap in cap_values:
        print(f"Monthly run-rate at {cap:.0f} h cap (blended {money(blended, currency)}/h): {money(cap * blended, currency)}")

    duration = commercials.get("estimated_duration_weeks", "NOT_FOUND")
    if isinstance(duration, list) and len(duration) == 2 and cap_values:
        weeks_min, weeks_max = duration
        low = cap_values[0] * blended * (weeks_min / 4.33)
        high = cap_values[-1] * blended * (weeks_max / 4.33)
        print(
            f"Indicative engagement value over {weeks_min}-{weeks_max} weeks: "
            f"{money(low, currency)} - {money(high, currency)}"
        )
    else:
        flags.append("engagement duration not anchored to dates — total value cannot be projected (end_date NOT_FOUND)")


def staff_augmentation(commercials, flags):
    currency = commercials.get("currency", "USD")
    team = commercials.get("team", [])
    computed_monthly = 0.0
    print("Team composition:")
    for member in team:
        fte = member.get("fte", 0) or 0
        fee = member.get("monthly_fee_per_fte", 0) or 0
        computed_monthly += fte * fee
        print(f"  {member.get('role', '?')}: {fte} FTE x {money(fee, currency)}/month")
    print(f"Computed monthly total: {money(computed_monthly, currency)}")

    stated_monthly = unwrap(commercials.get("stated_monthly_fee"))
    if isinstance(stated_monthly, (int, float)) and round(stated_monthly, 2) != round(computed_monthly, 2):
        flags.append(
            f"stated monthly fee {money(stated_monthly, currency)} does not match computed "
            f"{money(computed_monthly, currency)}"
        )

    term_months = commercials.get("term_months")
    if isinstance(term_months, (int, float)):
        computed_term = computed_monthly * term_months
        print(f"Computed term total ({term_months:.0f} months): {money(computed_term, currency)}")
        stated_term = unwrap(commercials.get("stated_term_total"))
        if isinstance(stated_term, (int, float)) and round(stated_term, 2) != round(computed_term, 2):
            flags.append(
                f"stated term total {money(stated_term, currency)} does not match computed "
                f"{money(computed_term, currency)}"
            )
    else:
        flags.append("term_months not set in baseline commercials — term total not computed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project_dir)
    baseline_path = project_dir / "baseline.json"
    if not baseline_path.exists():
        sys.exit(f"No baseline.json in {project_dir} — run sow-intake first.")

    with open(baseline_path, encoding="utf-8") as f:
        baseline = json.load(f)
    rate_card, rate_card_path = load_rate_card(project_dir)

    engagement = unwrap(baseline.get("engagement_type", "NOT_FOUND"))
    commercials = baseline.get("commercials", {})
    flags = []

    print(f"Project: {baseline.get('project_id', project_dir.name)}")
    print(f"Engagement type: {engagement}")
    print(f"Rate card: {rate_card_path}\n")

    if engagement == "fixed_price":
        fixed_price(commercials, flags)
    elif engagement == "time_and_materials":
        time_and_materials(commercials, rate_card, flags)
    elif engagement == "staff_augmentation":
        staff_augmentation(commercials, flags)
    else:
        flags.append(f"unknown or NOT_FOUND engagement type: {engagement!r}")

    if flags:
        print("\nFLAGS (copy into the brief's risk section — human resolution required):")
        for flag in flags:
            print(f"  - {flag}")
    else:
        print("\nNo commercial discrepancies detected.")


if __name__ == "__main__":
    main()
