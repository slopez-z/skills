#!/usr/bin/env python3
"""Deterministic conversion: t-shirt size -> hours range -> cost range.

The LLM proposes a size with a qualitative rationale; this lookup converts it
to numbers. The model never sees or invents the hours/dollars mapping.

Usage:
    python scripts/size_to_cost.py <S|M|L> [--project_dir projects/<project>/]
"""
import argparse
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("size", choices=["S", "M", "L"])
    parser.add_argument("--project_dir", default=None,
                        help="If the project has a negotiated rate-card.json, it overrides the default")
    args = parser.parse_args()

    with open(REPO_ROOT / "config" / "sizing.json", encoding="utf-8") as f:
        sizing = json.load(f)

    rate_card_path = REPO_ROOT / "config" / "rate-card.json"
    if args.project_dir:
        local = pathlib.Path(args.project_dir) / "rate-card.json"
        if local.exists():
            rate_card_path = local
    with open(rate_card_path, encoding="utf-8") as f:
        rate_card = json.load(f)

    size = sizing["sizes"][args.size]
    rate = rate_card["blended_hourly_rate"]
    print(json.dumps({
        "size": args.size,
        "hours_range": [size["hours_min"], size["hours_max"]],
        "blended_rate_usd_per_hour": rate,
        "cost_range_usd": [size["hours_min"] * rate, size["hours_max"] * rate],
        "rate_card": str(rate_card_path),
        "policy": sizing["policy"],
    }, indent=2))


if __name__ == "__main__":
    main()
