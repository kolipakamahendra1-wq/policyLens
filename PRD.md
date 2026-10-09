# PRD — PolicyLens AI

**AI Policy & Compliance Evidence Agent**

## 1. Overview

PolicyLens AI checks whether a proposed technical change satisfies internal engineering policies and produces an evidence-backed review package.

Today, reviewers manually compare each engineering proposal against many policy documents (security, privacy, data retention, access control, logging, deployment, API usage, change management). PolicyLens automates the comparison and leaves the final decision to a human.

## 2. Workflow

```text
1. Submit   →   2. Match   →   3. Evaluate   →   4. Approve   →   5. Package
```

| Step | Name     | What happens                                                                                     | Output                          |
| ---- | -------- | ------------------------------------------------------------------------------------------------ | ------------------------------- |
| 1    | Submit   | An engineer submits a change request and attaches any evidence they already have.                | Change request + extracted claims |
| 2    | Match    | The system finds the policies that apply and retrieves the exact sections, with citations.       | List of applicable requirements |
| 3    | Evaluate | Each requirement is checked against the evidence and given a status. Gaps trigger a request for missing evidence. | Control matrix + open gaps |
| 4    | Approve  | A human reviewer reads the findings and approves, rejects, or sends the request back.            | Review decision                 |
| 5    | Package  | The system assembles the final audit package.                                                    | Audit package                   |

### Statuses used in step 3

| Status               | Meaning                                              |
| -------------------- | ---------------------------------------------------- |
| `PASS`               | Evidence shows the requirement is met.               |
| `FAIL`               | Evidence shows the requirement is not met.           |
| `UNKNOWN`            | Not enough evidence to decide.                       |
| `NEEDS_HUMAN_REVIEW` | High-risk or ambiguous; a reviewer must decide.      |

## 3. Example

**Request:** "We are deploying a new API that stores customer information."

**Policies checked:** data classification, retention, access control, logging, deployment.

**Result:** `Needs Review`

| # | Finding                                | Status  |
| - | -------------------------------------- | ------- |
| 1 | Data retention period not specified    | Gap     |
| 2 | Encryption requirement                 | Satisfied |
| 3 | Access-control evidence missing        | Gap     |
| 4 | Audit logging requirement              | Satisfied |

**Evidence requested:** IAM configuration, retention configuration, logging configuration.

## 4. Features

| Feature             | Details                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------ |
| Policy ingestion    | Upload policies as PDF, Markdown, HTML, or DOCX.                                                 |
| Policy retrieval    | Hybrid retrieval: keyword search + vector search + reranking.                                    |
| Control mapping     | Requirement → Evidence → Status.                                                                 |
| Evidence collection | Attach screenshots, configuration files, API specifications, architecture documents.             |
| Review package      | Executive summary, control matrix, evidence references, open questions, risk register, reviewer checklist. |

## 5. Guardrails

The agent must:

- Never claim compliance without evidence.
- Separate policy text from model-generated interpretation.
- Cite the exact policy section used.
- Mark uncertain decisions as `UNKNOWN`.
- Require human review for high-risk decisions.
- Never modify production systems.

## 6. Tech Stack

| Layer          | Technologies                                         |
| -------------- | ---------------------------------------------------- |
| Backend        | Python, FastAPI, Pydantic, PostgreSQL                |
| AI             | Claude API, LangGraph, Sentence Transformers, Reranker |
| Retrieval      | pgvector, BM25                                       |
| Frontend       | React, TypeScript, Tailwind CSS                      |
| Security       | OAuth2/JWT, RBAC, Encryption, Audit logs             |
| Infrastructure | Docker, GitHub Actions, AWS/GCP/Azure                |

## 7. API

| Workflow step | Method | Endpoint        |
| ------------- | ------ | --------------- |
| Setup         | `POST` | `/policies`     |
| 1. Submit     | `POST` | `/reviews`      |
| 1. Submit     | `POST` | `/evidence`     |
| 2. Match      | `GET`  | `/controls`     |
| 3. Evaluate   | `POST` | `/evaluate`     |
| 3. Evaluate   | `GET`  | `/reviews/{id}` |
| 4. Approve    | `POST` | `/approve`      |
| 5. Package    | `GET`  | `/audit/{id}`   |

## 8. Evaluation

Create 50 synthetic policy-review cases and measure:

- Policy retrieval accuracy
- Control classification accuracy
- Evidence grounding
- False compliance rate
- Missing-evidence detection
- Human reviewer agreement

## 9. Repository

```text
policylens-ai/
├── backend/
├── agents/
├── policies/
├── retrieval/
├── evidence/
├── evaluation/
├── api/
├── frontend/
├── data/
├── tests/
├── infrastructure/
├── .github/
│   └── workflows/
├── README.md
└── PRD.md
```

## 10. Delivery

| Phase | Scope                                                              |
| ----- | ------------------------------------------------------------------ |
| 1     | Policy ingestion, hybrid retrieval, and citations                  |
| 2     | Control/evidence schema, evaluation agent, uncertainty handling    |
| 3     | Human approval workflow, audit package, and review screens         |
| 4     | Docker, CI/CD, and cloud deployment                                |
