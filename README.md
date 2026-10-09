# PolicyLens AI

**An AI policy and compliance evidence agent.** PolicyLens checks whether a proposed technical change satisfies internal engineering policies and produces an evidence-backed review package. A human reviewer makes the final decision.

Reviewers today compare each engineering proposal by hand against many policy documents: security, privacy, data retention, access control, logging, deployment, API usage and change management. PolicyLens finds the policies that apply, checks every requirement against the attached evidence, cites the exact policy section, asks for whatever evidence is missing, and assembles the audit package.

It runs entirely on **free, local models**. The default is Ollama `qwen2.5:3b` for evaluation and `nomic-embed-text` for embeddings, so there are no paid API calls.

## Workflow

```text
1. Submit   →   2. Match   →   3. Evaluate   →   4. Approve   →   5. Package
```

| Step | What happens | API |
|---|---|---|
| Setup | Upload policies (PDF, Markdown, HTML, DOCX); they are split into cited sections and requirements | `POST /policies` |
| 1. Submit | An engineer describes the change and attaches evidence; claims are extracted | `POST /reviews`, `POST /evidence` |
| 2. Match | Hybrid retrieval (BM25 + pgvector, reciprocal rank fusion, rerank) finds applicable requirements | `GET /controls?review_id=` |
| 3. Evaluate | Each requirement is checked against the evidence and guardrails are applied | `POST /evaluate`, `GET /reviews/{id}` |
| 4. Approve | A reviewer approves, rejects or sends the request back | `POST /approve` |
| 5. Package | Executive summary, control matrix, evidence references, open questions, risk register, reviewer checklist | `GET /audit/{id}` (`?format=md`) |

Statuses: `PASS` (evidence shows the requirement is met), `FAIL` (evidence shows it is not met), `UNKNOWN` (not enough evidence), `NEEDS_HUMAN_REVIEW` (high-risk or ambiguous).

## Guardrails

Every guardrail is deterministic code in [agents/guardrails.py](agents/guardrails.py) and [api/main.py](api/main.py). It runs after the model, whatever the model said.

| PRD guardrail | How it is enforced |
|---|---|
| Never claim compliance without evidence | A requirement with no evidence of its control type is `UNKNOWN` before the model is called. A `PASS` must cite real, relevant evidence ids; citations to non-existent evidence are dropped. A `PASS` on a requirement that sets a period (e.g. "retained for at least 1 year") is downgraded if the cited evidence states no period. |
| Separate policy text from interpretation | `policy_quote` must be a verbatim substring of the cited section; `interpretation` is a separate field, labelled "PolicyLens reading" in the UI and audit package. |
| Cite the exact policy section | Every finding carries `POLICY-KEY §n.n`. |
| Mark uncertain decisions UNKNOWN | Invalid or low-confidence model output becomes `UNKNOWN`. If the model is unreachable, a conservative rule-based check runs instead. |
| Human review for high-risk decisions | A high-risk `PASS` below 0.85 confidence, or high-risk evidence that is inconclusive, becomes `NEEDS_HUMAN_REVIEW`. Only reviewers can decide, never on their own request. Approving with open findings requires a written justification. Rejecting or returning always requires a comment. |
| Never modify production systems | The agent has no tools at all. It reads policies and evidence and returns findings. |

## Architecture

```text
frontend/ (React + TS + Tailwind, website with public landing + signed-in app)
   │  /api  (Vite proxy in dev, nginx in Docker)
api/main.py (FastAPI, OAuth2/JWT, RBAC: engineer | reviewer | admin, audit log)
   ├── policies/   parser (MD/HTML/DOCX/PDF → sections + requirements) and ingestion
   ├── retrieval/  embed (Ollama nomic-embed-text, hash fallback) + hybrid BM25/pgvector search
   ├── evidence/   Fernet-encrypted file store (sha256-addressed) + text/claim extraction
   ├── agents/     LangGraph: extract_claims → match → evaluate → guardrails → summarize
   │               evaluator: free LLM via OpenAI-compatible API, rule-based fallback
   └── backend/    config, SQLAlchemy models (Postgres 16 + pgvector), security, audit package
evaluation/       50 synthetic cases + metrics runner
infrastructure/   Dockerfiles, nginx, docker-compose
.claude/skills/policylens-review/   Claude Code skill + stdlib CLI client
```

## Run locally

Requirements: Python 3.12+, Node 22, Docker, and [Ollama](https://ollama.com) with the two free models:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

```bash
# Database (Postgres 16 + pgvector) on port 5433
docker run -d --name policylens-db -e POSTGRES_USER=policylens -e POSTGRES_PASSWORD=policylens \
  -e POSTGRES_DB=policylens -p 5433:5432 pgvector/pgvector:pg16

# Backend on port 8010 (seeds demo users and the 9 sample policies on first start)
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # .venv/bin on macOS/Linux
.venv/Scripts/python -m uvicorn api.main:app --port 8010

# Frontend on port 5174 (proxies /api to :8010)
cd frontend && npm install && npx vite --port 5174
```

Open http://localhost:5174 and sign in as `alice` (engineer), `rita` (reviewer) or `admin`. The password for each is `policylens` (set with `SEED_PASSWORD`). Sample evidence for the PRD example is in [data/evidence/](data/evidence/).

### Docker

```bash
docker compose -f infrastructure/docker-compose.yml -p policylens up --build
```

The app is served on http://localhost:8088. The backend reaches Ollama on the host through `host.docker.internal`.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://policylens:policylens@localhost:5433/policylens` | Postgres + pgvector |
| `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` | `http://localhost:11434/v1` / `qwen2.5:3b` / `ollama` | Any OpenAI-compatible endpoint. To use a free OpenRouter model, set `https://openrouter.ai/api/v1`, `<model>:free` and your key. |
| `USE_LLM` | `1` | `0` uses the rule-based evaluator only |
| `OLLAMA_URL` / `EMBED_MODEL` / `USE_OLLAMA_EMBED` | `http://localhost:11434` / `nomic-embed-text` / `1` | Embeddings. Falls back to a deterministic hashing embedder when unavailable. |
| `JWT_SECRET` | dev value | **Set in any shared deployment** |
| `EVIDENCE_KEY` | derived from `JWT_SECRET` | Fernet key for evidence at rest (`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`) |
| `SEED_PASSWORD` | `policylens` | Password for the seeded demo users |

## Policy format

Any document whose sections are headings works. In Markdown, the title is `#` and sections are `##`. Sentences containing *must*, *shall* or *required* become requirements. Optional metadata and per-requirement tags give precise risk and evidence mapping:

```markdown
# Access Control Policy
Policy ID: SEC-ACCESS
Domain: access_control

## 2.2 Authentication
Administrative access must require multi-factor authentication (MFA). (risk: high; evidence: iam)
```

Without tags, risk and evidence types are inferred from keywords ([backend/taxonomy.py](backend/taxonomy.py)).

## Tests and evaluation

```bash
.venv/Scripts/python -m pytest -q                         # 22 tests; needs the Postgres container
.venv/Scripts/python -m evaluation.run_eval               # offline: rule-based, deterministic (CI)
.venv/Scripts/python -m evaluation.run_eval --live --limit 10   # free local LLM
```

[evaluation/generate_cases.py](evaluation/generate_cases.py) creates 50 seeded synthetic cases. Each mixes change topics, and each control area gets evidence that meets the policy, visibly violates it, or is missing. That gives ground truth for every requirement.

Results (2026-10-09). The offline run covers all 50 cases; the live run covers the first 10, because a local 3B model takes about 2.5 minutes per case:

| Metric | Offline (rules + hash embeddings) | Live (qwen2.5:3b + nomic-embed-text) |
|---|---|---|
| Policy retrieval recall | 0.920 | 0.976 |
| Control classification accuracy (strict) | 0.697 | 0.457 |
| Control classification accuracy (counting `NEEDS_HUMAN_REVIEW` as safe) | 1.000 | 0.728 |
| Evidence grounding (cited evidence is of the right control type) | 0.904 | 0.895 |
| **False compliance rate** (PASS where truth is not PASS) | **0.000** | **0.000** |
| Missing-evidence detection | 0.884 | 1.000 |
| Human reviewer agreement | 0.68 | 0.60 |
| Avg. latency per case | <0.1 s | 146 s |

How to read these numbers:
- The false-compliance rate of zero comes from the guardrails, not from the model. In the live run the model claimed PASS several times without support, and each time a guardrail downgraded it. One example: "logs retained for at least 1 year" when the evidence states no period. CI fails if the offline false-compliance rate is ever above zero.
- The small local model is over-cautious: it often answers UNKNOWN for evidence that does meet the requirement. That is why strict accuracy is lower live than with rules. It also makes arithmetic slips; in one demo it called 2555 days longer than 7 years. Errors in this direction cost reviewer time but never produce a false PASS. A larger free model, for example via `LLM_MODEL`, should raise accuracy without changing any code.
- Grounding and missing-evidence detection fall short of 1.0 mostly because some evidence legitimately matches several control types. An IAM policy that names the data owner is one example.
- Reviewer agreement is limited because PolicyLens deliberately recommends "send back" whenever any matched requirement lacks evidence.

## Claude Code skill

[.claude/skills/policylens-review](.claude/skills/policylens-review/SKILL.md) teaches Claude to run a review end to end through the bundled stdlib client (`scripts/policylens.py`) and to report findings faithfully. The skill was tested with skill-creator's with-skill vs. baseline eval loop; the prompts are in [evals/evals.json](.claude/skills/policylens-review/evals/evals.json).

## Security notes

- OAuth2 password flow with HS256 JWTs and role-based access (engineer submits, reviewer decides, admin does both and manages policies).
- Evidence files are encrypted at rest with Fernet and addressed by SHA-256. Hashes are listed in the audit package.
- Every login, upload, evaluation, decision, download and package export is written to the audit log (`GET /audit-log`, also shown on the Activity page).
- Uploads are capped at 10 MB. CORS is restricted to configured origins.
- The demo users and default secrets are for local use only.
