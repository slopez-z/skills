# Skills for PMs / DMs

> Agentic Claude skills that put guardrails around software delivery — built by a delivery PM, for project and delivery managers.

Straight from my `.claude/` directory. Two skills I run on real delivery work: one turns a Statement of Work into living, cited project memory; the other guards that baseline against scope creep — both with a human holding the final pen.

## The problem they solve

Most "AI for PMs" tooling stops at summarizing a call or drafting a status update. The parts of delivery that actually leak money — scope interpretation, SOW intake, change-request discipline — are the parts where an LLM left unsupervised is a liability: it will confidently cite a clause that doesn't exist, invent an effort estimate, or draft something client-facing that should never have left your outbox.

These skills are built inside-out from that risk. The model reads, classifies, and drafts. Deterministic scripts handle anything that must never be guessed — citation checks, hours-and-cost math. A human approves anything with consequences. The result is closer to a delivery analyst who always shows their sources than to a chatbot with opinions.

## The two skills

**`sow-intake`** — runs first. Reads a SOW and produces the project's persistent baseline: a machine-readable `baseline.json` and a human-readable Delivery Brief. Every extracted value carries a verbatim citation to the source clause. Missing fields are recorded as `NOT_FOUND`, conflicting values are flagged rather than silently resolved, and all money and date arithmetic is done by script — never by the model.

**`scope-sentinel`** — runs after. Takes an incoming client request (email, meeting minutes, a chat message) and classifies it against that baseline: in-scope, out-of-scope, or ambiguous. Each call cites the exact clause, sizes the effort with a t-shirt estimate, and drafts a change request for human approval. It's engagement-aware — the question it asks itself changes for fixed-price vs. time-and-materials vs. staff-augmentation work.

Together they form a small pipeline: a SOW becomes a verified baseline, and that baseline becomes the reference every future request is measured against.

## Design principles

The skills are opinionated about one thing: **where the model is allowed to be trusted, and where it isn't.**

- **Division of labor.** The LLM classifies and drafts. Scripts verify citations and do all arithmetic. The model never states an hours or dollar figure it didn't get from a script.
- **No claim without a citation.** Every classification and every extracted field quotes the source verbatim, and the quote is validated against the document. A value whose citation fails validation isn't downgraded politely — it ceases to exist and routes to a human.
- **A human holds the pen.** Nothing client-facing is ever sent or marked as sent. Change requests and baselines stay drafts until a person approves them; only then is anything logged.
- **Fail loud, not confident.** Given an incomplete or contradictory SOW, the correct output is a baseline full of `NOT_FOUND`s and risk flags — not a clean-looking brief that papers over the gaps. "I couldn't find the end date; human review required" is the feature, not the bug.

## Repo structure

```
.
├── sow-intake/
│   ├── SKILL.md
│   ├── scripts/        # citation validation, revenue & date math
│   ├── schemas/        # baseline.schema.json
│   └── templates/      # delivery-brief.md
├── scope-sentinel/
│   ├── SKILL.md
│   ├── scripts/        # citation validation, size→cost, event logging
│   ├── templates/      # change-request.md
│   └── config/         # qualitative sizing definitions
└── README.md
```

## Using them

These are Claude skills (Claude Code / Claude apps). Drop a skill folder into your skills directory and Claude picks it up automatically by its `description`:

```bash
# user-level (available everywhere)
cp -r sow-intake scope-sentinel ~/.claude/skills/

# or project-level (scoped to one repo)
cp -r sow-intake scope-sentinel .claude/skills/
```

Then just ask — *"run intake on this SOW"* or *"is this request in scope?"* — and the relevant skill triggers. Both expect a `projects/<project>/` working folder; see each `SKILL.md` for the exact inputs and the human-approval gates.

## A note on scope

These were built for my own delivery work and are shared as a reference for how agentic skills can be made safe enough to trust with client-sensitive workflows. They're a working reference, not a product. No client data ships in this repo.
