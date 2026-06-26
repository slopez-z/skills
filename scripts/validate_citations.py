#!/usr/bin/env python3
"""Verify that every citation quote in a baseline (or any JSON containing
citation objects) exists verbatim in the source SOW.

This is the deterministic anti-hallucination gate: a value whose citation
cannot be found in the source document is rejected. The model must then set
the field to NOT_FOUND and flag it for human review.

Usage:
    python scripts/validate_citations.py <baseline.json> <sow.md|sow.txt>

Exit codes: 0 = all citations verified, 1 = at least one failure.
"""
import argparse
import json
import re
import sys


def normalize(text: str) -> str:
    """Whitespace- and typography-insensitive normalization."""
    replacements = {
        "\u2018": "'", "\u2019": "'",   # curly single quotes
        "\u201c": '"', "\u201d": '"',   # curly double quotes
        "\u2013": "-", "\u2014": "-",   # en/em dashes
        "\u00a0": " ",                   # non-breaking space
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Strip markdown formatting chars so a quote like "Engagement Model: Fixed
    # Price" matches the source "**Engagement Model:** Fixed Price", and table
    # cell quotes match their rows.
    text = re.sub(r"[*_`#|>]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def find_citations(node, path="$"):
    """Recursively collect (json_path, quote) for every citation object."""
    found = []
    if isinstance(node, dict):
        citation = node.get("citation")
        if isinstance(citation, dict) and citation.get("quote"):
            found.append((path, citation["quote"]))
        for key, value in node.items():
            if key != "citation":
                found.extend(find_citations(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_citations(value, f"{path}[{i}]"))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="JSON file containing citation objects")
    parser.add_argument("sow", help="Source SOW text/markdown file")
    args = parser.parse_args()

    with open(args.baseline, encoding="utf-8") as f:
        baseline = json.load(f)
    with open(args.sow, encoding="utf-8") as f:
        sow_text = normalize(f.read())

    citations = find_citations(baseline)
    if not citations:
        print("WARNING: no citation objects found in the input JSON.")
        sys.exit(1)

    failures = []
    for path, quote in citations:
        ok = normalize(quote) in sow_text
        status = "PASS" if ok else "FAIL"
        print(f"{status}  {path}")
        if not ok:
            failures.append((path, quote))

    print(f"\n{len(citations) - len(failures)}/{len(citations)} citations verified against source.")

    if failures:
        print("\nFAILED citations — set these fields to NOT_FOUND and add them to")
        print("extraction_meta.fields_pending_review, then re-run:")
        for path, quote in failures:
            preview = quote if len(quote) <= 90 else quote[:90] + "..."
            print(f'  {path}: "{preview}"')
        sys.exit(1)


if __name__ == "__main__":
    main()
