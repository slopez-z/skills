---
name: scope-sentinel
description: Compare an incoming client request (email, meeting minutes, chat message) against the project's SOW baseline and classify it as in-scope, out-of-scope, or ambiguous, with a verified citation to the exact clause, a t-shirt effort estimate, and a draft change request for human approval. Use this whenever the user asks to check, classify, or triage a client request against the SOW or scope, asks "is this in scope?", mentions scope creep or a change request, or drops a new file into a project's inbox folder.
---

# Scope Sentinel

Protects the delivery baseline. Reads a client request, compares it against `baseline.json`, and produces a classification with evidence plus a draft change request. Nothing it produces is client-facing until a human approves it.

## Division of labor (non-negotiable)

| Decision | Owner |
|----------|-------|
| Classification (in/out/ambiguous) and clause matching | LLM (you) |
| Citation verification | `scripts/validate_citations.py` |
| Size → hours → cost conversion | `scripts/size_to_cost.py` (you never see or state the money mapping yourself) |
| Approve / reject / discuss | Human — always |
| Changelog write | `scripts/log_event.py`, only after explicit human approval |

## Inputs

- The request: a file in `projects/<project>/inbox/` (or pasted text — save it to the inbox first so the source is traceable).
- The project's `baseline.json` and `sow.md` in the same folder. The folder determines the project; never compare a request against another project's baseline.
- `config/sizing.json` qualitative definitions (below) for sizing.

## Classification rules — engagement-type aware

Read `engagement_type` from the baseline first. The question changes by model:

| Engagement | The question to answer |
|------------|------------------------|
| `fixed_price` | Is the request covered by the scope sections, excluded by the exclusions, or neither? |
| `time_and_materials` | Scope sections still bound the work. A new workstream is `out_of_scope` of the defined sections, but frame the impact as **additional billable hours vs. the monthly cap** — and if the baseline records a cap contradiction, say the cap must be resolved before any commitment. |
| `staff_augmentation` | Is the request within the contracted **role mandate** and prioritization model? Outcome-based asks against a staff-aug contract get an `engagement_model_mismatch` note. |

Decision rules:

1. `in_scope`: a scope section or assumption explicitly covers it. Cite it. No CR needed; note any consumable it draws down (e.g., revision rounds).
2. `out_of_scope`: an exclusion covers it, or it is clearly a new capability/integration not in any scope section. Cite the exclusion or the nearest scope boundary. Draft a CR.
3. `ambiguous`: the SOW neither covers nor excludes it, or coverage depends on interpretation. **Ambiguity always routes to human review — never resolve it yourself.** State precisely what makes it ambiguous and what question a human must answer.
4. Every classification cites a verbatim quote. Run `python scripts/validate_citations.py` against a temp JSON of your citations (or include them in the CR and validate). A classification whose citation fails validation downgrades to `ambiguous` + human review.
5. Also surface non-scope risks you notice (e.g., a request involving patient or health data → privacy/compliance flag).

## Effort sizing (only for out_of_scope, or ambiguous-if-approved)

Propose a t-shirt size using ONLY these qualitative definitions:

- **S** — copy/config change within existing flows; no new integration, no new data.
- **M** — new flow variant or notification path built on existing integrations and existing data.
- **L** — new flow plus a new integration or new external data source.
- Anything beyond L: do not size it. Recommend re-scoping (SOW amendment) per the XL rule.

Give a 2–3 line rationale tied to the request's facts. Then run `python scripts/size_to_cost.py <S|M|L> --project_dir projects/<project>/` and paste its output verbatim. You never state hours or dollar figures the script did not produce, and you always present ranges, never a single number.

## Output and human gate

1. Fill `templates/change-request.md` → save as `projects/<project>/cr-<date>-<slug>.md` (for `in_scope`, a short classification note in chat is enough).
2. Present the classification, citation, size, and CR draft to the user and **stop**. Ask for a decision: approve / reject / discuss.
3. Only after the human explicitly approves or rejects, log the event:
   `python scripts/log_event.py projects/<project>/ --json '{"request_source": "...", "classification": "...", "cited_section": "...", "size": "...", "hours_range": [..], "cost_range_usd": [..], "decision": "approved|rejected", "approver": "<name>"}'`
4. Never send, simulate sending, or mark as sent any client-facing message.

The changelog (`scope-changelog.jsonl`) is append-only structured data. Across projects it becomes the portfolio dataset for scope-erosion analytics — keep events complete and consistent.
