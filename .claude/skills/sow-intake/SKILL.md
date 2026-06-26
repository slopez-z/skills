---
name: sow-intake
description: Turn a Statement of Work (SOW) into a structured Delivery Baseline (baseline.json) plus a human-readable Delivery Brief with mandatory citations, risk flags, and a kickoff checklist. Use this whenever the user asks to process, analyze, summarize, onboard, or "run intake" on a SOW, contract, or statement of work, or drops a new SOW file into a project folder, or asks for a delivery brief, baseline, or kickoff checklist for a new project.
---

# SOW Intake

Converts a SOW into the project's persistent memory: `baseline.json` (machine-readable, consumed by scope-sentinel) and `delivery-brief.md` (human-readable). The SOW stops being a dead PDF and becomes the living baseline that protects the delivery.

## Division of labor (non-negotiable)

| Decision | Owner |
|----------|-------|
| Field extraction, classification, risk-flag detection | LLM (you) |
| Citation verification | `scripts/validate_citations.py` |
| ALL money and date arithmetic (totals, schedules, run-rates) | `scripts/compute_revenue.py` |
| Final sign-off of the brief | Human |

You never compute revenue, sum payment schedules, or multiply rates by hours. You extract the numbers the SOW states, with citations, and the script does the math.

## Inputs

- A project folder under `projects/<client>-<project>/` containing the SOW (`sow.md` or `sow.pdf`). The folder name IS the `project_id` — this is how projects are differentiated. One folder per project; all outputs stay inside it.
- Rate card: use `projects/<project>/rate-card.json` if present (negotiated client rates); otherwise fall back to `config/rate-card.json`.

## Process

1. **Read** the SOW in the project folder and `schemas/baseline.schema.json`.
2. **Extract** every field defined in the schema. Hard rules:
   - Every extracted value carries a `citation` with the section number and a **verbatim quote** copied character-for-character from the SOW. Do not paraphrase inside `quote`.
   - If a field is not in the document, set it to the literal string `NOT_FOUND` and list it in `extraction_meta.fields_not_found`. Never infer, never fill with a plausible value. "Estimated duration 10–12 weeks" with no anchored kickoff date means `end_date: NOT_FOUND`.
   - If the SOW states **conflicting values** for the same fact (e.g., two different monthly hour caps), record ALL stated values and raise a `hours_cap_contradiction` / `numeric_contradiction` risk flag. Never silently pick one.
   - Conventions: `start_date` = first contractual milestone or term start; `end_date` = last contractual milestone or term end; a milestone explicitly marked "TBD" is recorded as `TBD` (with flag `milestone_tbd`), which is different from `NOT_FOUND`.
3. **Detect risk flags** using the taxonomy in the schema. Look specifically for: missing assumptions/exclusions sections, undefined references ("standard SLAs apply" with no definition), TBD or missing dates, contradictory numbers, scope language that mismatches the engagement model (e.g., outcome-based deliverable commitments inside a staff augmentation SOW), prioritization fully delegated to the client, unusual penalties.
4. **Write** `baseline.json` in the project folder.
5. **Validate citations**: run `python scripts/validate_citations.py projects/<project>/baseline.json projects/<project>/sow.md`. If any citation fails, do NOT keep the value: set the field to `NOT_FOUND`, add it to `extraction_meta.fields_pending_review`, and re-run until the validator passes. A value without a verified citation does not exist.
6. **Compute commercials**: run `python scripts/compute_revenue.py projects/<project>/`. Paste its output verbatim into the brief. If the script reports flags (e.g., cap conflict, schedule mismatch), copy them into the risk flags section. Never "fix" the numbers yourself.
7. **Write** `delivery-brief.md` in the project folder following `templates/delivery-brief.md`. The kickoff checklist is generated from the assumptions (client dependencies become checklist items with owners) and milestones. All `NOT_FOUND` and pending-review fields go in "Fields requiring human review" — these block kickoff sign-off.
8. **Report** to the user: one-line summary, count of verified citations, list of NOT_FOUND fields, list of risk flags. State explicitly that the brief requires human review.

## Failure behavior

If the SOW is incomplete, ambiguous, or contradictory, the correct output is a baseline full of `NOT_FOUND`s and risk flags — not a confident-looking brief. Saying "I could not find the end date; human review required" is a feature of this system, not a failure.
