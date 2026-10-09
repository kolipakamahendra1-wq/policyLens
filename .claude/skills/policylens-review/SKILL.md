---
name: policylens-review
description: Run an evidence-backed policy compliance review of an engineering change with PolicyLens, covering ingesting policies, submitting the change, attaching evidence, evaluating, reading the control matrix, and producing the audit package. Use this whenever someone asks whether a change, design, API, data store or deployment complies with internal security, privacy, retention, access-control, logging, deployment, API or change-management policy. Also use it when they want to know which policies apply, what evidence is missing, or want a compliance/audit package or reviewer decision, even if they never say "PolicyLens".
---

# PolicyLens review

PolicyLens checks a proposed technical change against internal policies. It returns a status for every applicable requirement, each with a citation to the exact policy section and the evidence it relied on. A human reviewer makes the final decision. Your job with this skill is to drive that workflow and report its findings faithfully, not to judge compliance yourself.

## Prerequisites

- The PolicyLens API is running (default `http://localhost:8010`; override with `POLICYLENS_URL`). Check with `curl -s $POLICYLENS_URL/health`.
  - If it isn't running, start it from the repo root: `docker start policylens-db`, then `.venv/Scripts/python -m uvicorn api.main:app --port 8010`.
- Evaluation uses a free local model (Ollama `qwen2.5:3b`). If Ollama is down, PolicyLens falls back to rule-based checks and still works.
- Demo users (password `policylens`): `alice` (engineer), `rita` (reviewer), `admin`.

## Quick start

All commands use the bundled stdlib client `scripts/policylens.py`, which needs no installs:

```bash
C=.claude/skills/policylens-review/scripts/policylens.py
python $C login alice policylens
python $C submit "Customer API" "We are deploying a new API that stores customer information."
python $C evidence 3 data/evidence/iam-policy.json            # repeat per file
python $C controls 3                                          # which requirements apply, with citations
python $C evaluate 3                                          # can take a few minutes with the local model
python $C audit 3 --md > audit-review-3.md
```

## Workflow

1. **Submit.** Write the change description in plain language. Include the data involved, where it's stored, who can access it and how it ships. Retrieval matches policies on this text, so vague descriptions match fewer policies.
2. **Attach evidence.** Upload the real artefacts the user has: configs, IAM policies, OpenAPI specs, DPIAs, runbooks. Pass `--type` only when the file name and content don't make the type obvious. For screenshots, add a `--note` describing what they show, because images aren't read. Never write evidence files yourself to make a requirement pass. Fabricated evidence defeats the purpose of the review, and the audit package records every file's sha256.
3. **Preview controls** (optional). `controls <id>` lists the matched requirements, with the evidence types each one needs, before evaluation. It's useful when the user asks "which policies apply?"
   - Matching is retrieval, not judgement, so it can miss a policy the description only implies. For example, a record-lookup tool implies audit logging.
   - Run `policies` and compare. If a policy plausibly applies but wasn't matched, list it under its own heading, "Possibly applicable, not matched by PolicyLens".
   - To have it checked, add the missing aspect to the description in a new review. Keep the two lists separate so the reader can tell the tool's output from your judgement.
4. **Evaluate.** `evaluate <id>` runs the agent and prints findings sorted FAIL, then NEEDS_HUMAN_REVIEW, then UNKNOWN, then PASS.
5. **Report.** Summarise for the user using the structure below.
6. **Decide** (reviewer role only, and not on your own submission). `decide <id> approve|reject|return "<comment>"`. Only do this when the user explicitly asks you to record a decision, because it is the human sign-off. A comment is required to reject or return, and to approve while findings are open.
7. **Package.** `audit <id> --md` produces the audit package: executive summary, control matrix, evidence references, open questions, risk register and reviewer checklist.

## Reading the results

| Status | Meaning | What to tell the user |
|---|---|---|
| `PASS` | Cited evidence shows the requirement is met | Name the evidence (E-number and file) |
| `FAIL` | Evidence shows it is not met | Quote the policy text and what in the evidence contradicts it |
| `UNKNOWN` | Not enough evidence | List the evidence type requested |
| `NEEDS_HUMAN_REVIEW` | High-risk or ambiguous | Say a reviewer must decide, and why |

Each finding carries two kinds of text: `policy` (verbatim policy wording) and `reading` (the model's interpretation). Keep them separate when you report: quote policy text as policy, and attribute interpretations to PolicyLens. Reviewers need to know which sentences are binding and which are a model's opinion.

`guardrail:` lines show where deterministic checks overrode the model, for example a PASS with no cited evidence, or a PASS on a period requirement when the evidence states no period. Mention them. They are often the most important part of the review.

## Report structure

```markdown
## PolicyLens review #<id>: <title>
**Result:** <Compliant | Needs Review> (<n> requirements, <pass>/<fail>/<unknown>/<human> pass/fail/unknown/human review)

### Blocking findings
- <STATUS> <citation>: "<policy text>". <one-line reading>, evidence <E#|none>

### Evidence still needed
- <evidence type>: needed for <citations>

### Passed with evidence
- <citation>: <E# file>

Final decision rests with a human reviewer. Audit package: `audit <id> --md`.
```

## Ground rules, and why

- **Don't upgrade a status.** If PolicyLens says UNKNOWN, the honest answer is "not shown yet", even if the change sounds fine. False compliance is the costliest error this tool exists to prevent.
- **Small local models make mistakes.** Arithmetic mistakes are especially common, such as calling 2555 days longer than 7 years. When a FAIL or PASS reading contradicts its own cited evidence, point that out for the reviewer rather than silently correcting the status.
- **Check that evidence belongs to the change.** A config whose header or keys name a different service may not apply. Say so rather than letting its PASSes stand silently.
- **Read-only.** The workflow never touches production systems. Don't run deployments or change infrastructure as part of a review.

## Troubleshooting

- `Cannot reach PolicyLens`: the API isn't running or `POLICYLENS_URL` is wrong. Port 8000 may belong to another app; PolicyLens uses 8010.
- `HTTP 401`: the token expired, so run `login` again.
- `HTTP 403 Reviewers cannot decide on their own change request`: log in as a different reviewer.
- `HTTP 409 ... run /evaluate first`: decisions need an evaluated review. Adding evidence to a returned review moves it back to submitted.
- Evaluation is slow: each requirement with matching evidence is one local-model call, so a review with 15 or more such requirements takes minutes. That's expected.
