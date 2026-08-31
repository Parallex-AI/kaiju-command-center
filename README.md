# Kaiju Command Center

AI agent lab for Kaiju Digital.

## Current milestone

**V5.24 — Documentation and Planning Hardening** (branch: `v5.24-documentation-planning-hardening` · base: `v5.23.0-beta` / master `3963f9d`)

V5.24 hardens the planning and control documentation produced in V5.18–V5.23. It addresses three identified gaps in the control framework: how Claude Code evaluates authorization phrase validity, what evidence closes the 17 V5.23 gaps, and how ceremony windows are planned and integrity-checked. **Documentation-only hardening. Real OAuth remains NOT APPROVED.** No real credentials. No OAuth execution. No auth URL. No browser. No callback URL. No auth code. No token exchange. No Secret Manager. No Google Ads API. No GCP. No deploy. No IAM/API/billing changes. `GOOGLE_ADS_LIVE_ENABLED=false` throughout.

**Phase 1 — Implementation plan** (`docs/V5_24_IMPLEMENTATION_PLAN.md`): V5.24 7-phase hardening plan; hardening targets (authorization phrase validation, gap closure evidence, ceremony window integrity); credential boundary (H-01–H-10); safety envelope (I-01–I-10); deferred items; Phase 7 authorization requirements. Documentation-only. Does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or `GOOGLE_ADS_LIVE_ENABLED=true` activation.

**Phase 2 — Authorization phrase validation protocol** (`docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md`): phrase anatomy (8 elements B-01–B-08); 15 validity criteria (C-01–C-15; all conjunction); 30 rejection patterns (D-01–D-30; phrase, scope, channel, timing defects); 6 response scenarios (E.1–E.6); channel validation (5 evidence items F-E1–F-E5); version/step binding (G.1–G.3); ambiguity resolution; escalation protocol; recording rules (J-08 absolute phrase non-logging prohibition); 10 stop conditions (K-01–K-10). Documentation-only. Does not authorize OAuth, credentials, or any live step.

**Phase 3 — Gap closure evidence requirements** (`docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md`): 6 evidence types; 3 sensitivity tiers; per-gap evidence specifications for all 17 V5.23 gaps (H-01–H-17); evidence sufficiency matrix; partial closure states (OPEN/PARTIALLY_ADDRESSED/ADDRESSED); evidence expiry; assertion vs. verification distinction; 4 gap clusters; minimum gap set for A1 proposal (9 gaps + 4 pre-proposal requirements); 7 stop conditions (J-01–J-07). Documentation-only. All 17 gaps remain OPEN.

**Phase 4 — Ceremony window integrity protocol** (`docs/GOOGLE_ADS_CEREMONY_WINDOW_INTEGRITY_PROTOCOL.md`): 10 window planning prerequisites (B-01–B-10); dry-run currency (30-day hard / 21-day warning + refresh protocol); smoke suite and safety grep currency; window sizing guide (E-R1–E-R8 + per-step budgets + 4 sizing rules); overlap detection (4 checks H-C1–H-C4); abort procedure (9 steps I-A1–I-A9); restart rules (5 rules I-R1–I-R5; no carry-forward); extension prohibition + emergency extension policy requirements; window integrity verification (8+5+5 checks at open/mid/close); 10 stop conditions (L-01–L-10). Documentation-only. Does not authorize OAuth, credentials, or any live step.

**Phase 5 — Hardening cross-reference review** (`docs/V5_24_HARDENING_REVIEW.md`): hardening verdict `HARDENED`; zero contradictions with V5.18–V5.23 control corpus; 22/22 V5.23 controls PASS (4 controls strengthened); 610 demo assertions unchanged; 211 V5.24 new control clauses; 18 sensitive categories absent; safety grep CLEAN; smoke suites 35/35 and 8/8 PASS; all 17 gaps remain OPEN; V5.23 `READY_TO_PROPOSE` verdict unchanged. Documentation-only.

**Phase 6 — Branch closure docs and release notes** (`docs/V5_24_BRANCH_CLOSURE.md` · `docs/RELEASE_NOTES_V5_24_0_BETA.md`): hardening verdict `HARDENED`; 610 baseline demo assertions + 211 V5.24 clauses = 821 combined; 25 security confirmations; 14 NOT APPROVED boundaries; closure decision READY FOR PHASE 7 AUTHORIZATION ONLY. Real OAuth remains NOT APPROVED. No merge/tag/push/release performed.

*Prior milestone (V5.23 — controlled real OAuth execution planning) inline notes moved to previous-milestone section below.*

<details>
<summary>V5.23 — Controlled Real OAuth Execution Planning (shipped as v5.23.0-beta)</summary>

V5.23 designed the authorization architecture, per-step approval model (A1–A10), secret and credential handling boundary, stop conditions, and safety-check envelope required before any first controlled real OAuth execution can be proposed. Verdict: `READY_TO_PROPOSE`. Real ceremony authorization NOT GRANTED. 17 gaps (H-01–H-17) documented. 610 aggregate assertions. Merged to master `3963f9d`; tagged `v5.23.0-beta`; GitHub Release published 2026-08-24. See [V5.23 Branch Closure](docs/V5_23_BRANCH_CLOSURE.md) and [v5.23.0-beta Release Notes](docs/RELEASE_NOTES_V5_23_0_BETA.md).

</details>

<details>
<summary>V5.22 — Controlled Real OAuth Ceremony Dry Run Execution (shipped as v5.22.0-beta)</summary>

V5.22 executed a full dry-run rehearsal of the controlled Google Ads OAuth onboarding ceremony using V5.21 controls, validators, runbooks, and redacted placeholders only. Result PASS (dry-run only). Real ceremony authorization NOT GRANTED. 610 aggregate explicit assertions. 16 gaps documented. 16 NOT APPROVED boundaries. Merged to master `4217652`; tagged `v5.22.0-beta`; GitHub Release published 2026-08-24. See [V5.22 Branch Closure](docs/V5_22_BRANCH_CLOSURE.md) and [v5.22.0-beta Release Notes](docs/RELEASE_NOTES_V5_22_0_BETA.md).

*V5.22 phase-by-phase notes (Phases 1–7) preserved in commit history and in [V5.22 Implementation Plan](docs/V5_22_IMPLEMENTATION_PLAN.md).*

</details>

*Latest shipped:* **v5.23.0-beta — Controlled Real OAuth Execution Planning complete** — tag `v5.23.0-beta` · merge commit `3963f9d`. See [V5.23 Branch Closure](docs/V5_23_BRANCH_CLOSURE.md) and [v5.23.0-beta Release Notes](docs/RELEASE_NOTES_V5_23_0_BETA.md).

---

*Previous milestone:* **V5.23.0-beta — Controlled Real OAuth Execution Planning complete** — tag `v5.23.0-beta` · merge commit `3963f9d`. See [V5.23 Branch Closure](docs/V5_23_BRANCH_CLOSURE.md) and [v5.23.0-beta Release Notes](docs/RELEASE_NOTES_V5_23_0_BETA.md).

## Architecture

```
Demo Client (HTTP POST)
    ↓
Router HTTP Server  (FastAPI · localhost:8000)
    ↓
Router Core         (route_request · validation · dispatch)
    ↓
Ads Agent           (n8n_client · request type routing)
    ↓
n8n Webhook         (flows.kaiju.digital · production)
    ↓
JSON Response
```

## Quick start

**1. Start the Router server**

```bash
cd ~/kaiju/agents/router
~/kaiju/.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

**2. Run the Demo Client**

```bash
cd ~/kaiju/projects/demo-client
~/kaiju/.venv/bin/python3 client.py summary
~/kaiju/.venv/bin/python3 client.py cpa
~/kaiju/.venv/bin/python3 client.py conversions
~/kaiju/.venv/bin/python3 client.py raw
```

**3. Run the interactive chat client**

```bash
~/kaiju/.venv/bin/python3 chat_client.py
```

## Documentation

- [V0 Architecture](docs/V0_ARCHITECTURE.md)
- [V0 Runbook](docs/V0_RUNBOOK.md)
- [Roadmap](docs/ROADMAP.md)
- [V5.12 Release Notes](docs/V5_12_GCP_SECRET_MANAGER_RELEASE_NOTES.md)
- [GCP Secret Manager Runbook](docs/GCP_SECRET_MANAGER_RUNBOOK.md)
- [V5.13 Branch Closure](docs/V5_13_BRANCH_CLOSURE.md)
- [v5.13.0-beta Release Notes](docs/RELEASE_NOTES_V5_13_0_BETA.md)
- [V5.13 Manual GCP Validation Plan](docs/V5_13_MANUAL_GCP_VALIDATION_PLAN.md)
- [V5.13 Live GCP Validation Results](docs/V5_13_LIVE_GCP_VALIDATION_RESULTS.md)
- [V5.14 Branch Closure](docs/V5_14_BRANCH_CLOSURE.md)
- [v5.14.0-beta Release Notes](docs/RELEASE_NOTES_V5_14_0_BETA.md)
- [V5.15 Branch Closure](docs/V5_15_BRANCH_CLOSURE.md)
- [v5.15.0-beta Release Notes](docs/RELEASE_NOTES_V5_15_0_BETA.md)
- [V5.16 Branch Closure](docs/V5_16_BRANCH_CLOSURE.md)
- [v5.16.0-beta Release Notes](docs/RELEASE_NOTES_V5_16_0_BETA.md)
- [V5.17 Branch Closure](docs/V5_17_BRANCH_CLOSURE.md)
- [v5.17.0-beta Release Notes](docs/RELEASE_NOTES_V5_17_0_BETA.md)
- [Credential Lifecycle Runbook](docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md)
- [V5.17 Rate Limiting Design](docs/V5_17_RATE_LIMITING_DESIGN.md)
- [V5.18 Live GCP Fake Validation Plan](docs/V5_18_LIVE_GCP_FAKE_VALIDATION_PLAN.md)
- [V5.18 Live GCP Fake Validation Results](docs/V5_18_LIVE_GCP_FAKE_VALIDATION_RESULTS.md) (complete — Phases A–N PASS)
- [V5.18 Branch Closure](docs/V5_18_BRANCH_CLOSURE.md)
- [v5.18.0-beta Release Notes](docs/RELEASE_NOTES_V5_18_0_BETA.md)
- [V5.19 Implementation Plan](docs/V5_19_IMPLEMENTATION_PLAN.md)
- [V5.19 Branch Closure](docs/V5_19_BRANCH_CLOSURE.md)
- [v5.19.0-beta Release Notes](docs/RELEASE_NOTES_V5_19_0_BETA.md)
- [V5.20 Implementation Plan](docs/V5_20_IMPLEMENTATION_PLAN.md)
- [Google Ads Real Onboarding Checklist](docs/GOOGLE_ADS_REAL_ONBOARDING_CHECKLIST.md) — operator checklist only; does not authorize real onboarding
- [Google Ads First Live API Validation Plan](docs/GOOGLE_ADS_FIRST_LIVE_API_VALIDATION_PLAN.md) — design-only; does not authorize execution
- [V5.20 Final Readiness Review](docs/V5_20_FINAL_READINESS_REVIEW.md) — local readiness PASS; NOT approved for real execution
- [V5.20 Branch Closure](docs/V5_20_BRANCH_CLOSURE.md)
- [v5.20.0-beta Release Notes](docs/RELEASE_NOTES_V5_20_0_BETA.md)
- [V5.21 Implementation Plan](docs/V5_21_IMPLEMENTATION_PLAN.md) — planning only; does not authorize OAuth, real credentials, or Google Ads API
- [Google Ads OAuth Ceremony Checklist](docs/GOOGLE_ADS_OAUTH_CEREMONY_CHECKLIST.md) — documentation-only operator ceremony checklist; does not authorize OAuth or real onboarding
- [Google Ads Credential Handoff Protocol](docs/GOOGLE_ADS_CREDENTIAL_HANDOFF_PROTOCOL.md) — documentation-only secure handoff protocol; does not authorize real credential handoff or Secret Manager write
- [Google Ads OAuth Dry-Run Runbook](docs/GOOGLE_ADS_OAUTH_DRY_RUN_RUNBOOK.md) — documentation-only operator rehearsal runbook; does not authorize OAuth, real credentials, or execution
- [V5.21 Final Readiness Review](docs/V5_21_FINAL_READINESS_REVIEW.md) — local OAuth ceremony readiness PASS; NOT approved for real OAuth/credentials/token exchange/API/GCP/Secret Manager/live flag
- [V5.21 Branch Closure](docs/V5_21_BRANCH_CLOSURE.md) — merged, tagged v5.21.0-beta, GitHub Release published 2026-08-22
- [v5.21.0-beta Release Notes](docs/RELEASE_NOTES_V5_21_0_BETA.md)
- [V5.22 Implementation Plan](docs/V5_22_IMPLEMENTATION_PLAN.md) — planning only; does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or live flag activation
- [Google Ads OAuth Dry-Run Execution Packet](docs/GOOGLE_ADS_OAUTH_DRY_RUN_EXECUTION_PACKET.md) — documentation-only redacted packet template; does not authorize real OAuth execution, credentials, token exchange, GCP, or live flag activation
- [V5.22 Dry-Run Execution Validator](openclaw/oauth_dry_run_execution.py) — local-only; validates dry-run packet completeness and no-execution confirmations; pure stdlib; does not execute dry-run or authorize real OAuth
- [V5.22 Dry-Run Execution Results](docs/V5_22_DRY_RUN_EXECUTION_RESULTS.md) — local dry-run result PASS; redacted evidence only; does not authorize real OAuth execution, credentials, token exchange, GCP, or live flag activation
- [V5.22 Stop-Condition and Rollback Rehearsal Results](docs/V5_22_STOP_AND_ROLLBACK_REHEARSAL_RESULTS.md) — documentation-only rehearsal result PASS; 26 stop conditions walked through; rollback and emergency revoke rehearsed as no-real-state walkthrough; no real rollback/revoke, credentials, OAuth, token exchange, GCP, Secret Manager, Google Ads API, or live flag activation
- [V5.22 Final Dry-Run Review](docs/V5_22_FINAL_DRY_RUN_REVIEW.md) — final dry-run verdict PASS (dry-run only); 610 explicit assertions; 16 gaps documented; 16 NOT APPROVED actions; real ceremony NOT APPROVED; does not authorize real OAuth, credentials, token exchange, GCP, Secret Manager, Google Ads API, or live flag activation
- [V5.22 Branch Closure](docs/V5_22_BRANCH_CLOSURE.md) — READY FOR PHASE 8 AUTHORIZATION; 12 sections; phase completion matrix Phases 1–6 PASS; 21 security confirmations; 16 gaps; 16 NOT APPROVED boundaries; closure decision READY FOR MERGE/TAG/RELEASE AUTHORIZATION ONLY
- [v5.22.0-beta Release Notes](docs/RELEASE_NOTES_V5_22_0_BETA.md)
- [V5.23 Implementation Plan](docs/V5_23_IMPLEMENTATION_PLAN.md) — planning only; 10-phase roadmap; authorization architecture (10 live steps A1–A10); secret and credential handling boundary (10 rules G1–G10); 25 stop conditions (H-01–H-25); safety-check envelope (26 checks I-01–I-26); does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or live flag activation
- [Google Ads Real OAuth Authorization Packet](docs/GOOGLE_ADS_REAL_OAUTH_AUTHORIZATION_PACKET.md) — documentation-only template; A1–A10 live step table; 10 verbatim authorization phrase templates; 20 approval validity rules; 23-item pre-authorization checklist; 29 stop conditions; all fields placeholder-only in committed form; does not authorize real OAuth, credentials, token exchange, Secret Manager, Google Ads API, GCP, or live flag activation
- [Google Ads Real Credential Intake Protocol](docs/GOOGLE_ADS_REAL_CREDENTIAL_INTAKE_PROTOCOL.md) — documentation-only protocol; 15 sections (A–O); 16-class credential matrix; 4 approved channel classes + 17 forbidden channels; 9 role placeholders; 18-step intake sequence G1–G18; Secret Manager handoff boundary; 35 stop conditions K-01–K-35; 31-item pre-intake checklist L-01–L-31; 13-step incident protocol M1–M13; all examples placeholder-only; does not authorize real credential intake, OAuth, token exchange, Secret Manager write, Google Ads API, GCP, or live flag activation
- [Google Ads Real OAuth Execution Runbook](docs/GOOGLE_ADS_REAL_OAUTH_EXECUTION_RUNBOOK.md) — documentation-only runbook; 15 sections (A–O); ceremony identity (12 fields; default committed status `DRAFT`); 10 operator role placeholders with 6 attributes each; time-boxed execution window (6 fields + 8 rules); 38-item pre-execution gate checklist F-01–F-38; 38-step execution sequence G1–G38 with mandatory pause after every A-step; 10 per-step execution cards A1–A10; 50 stop conditions I-01–I-50; 10-item rollback/revoke readiness checklist J-01–J-10; post-execution verification template; 33-item final go/no-go checklist L-01–L-33 (NO_GO on any unchecked item); 11 allowed + 17 forbidden evidence categories; all fields placeholder-only in committed form; does not authorize real OAuth, credentials, token exchange, Secret Manager write, Google Ads API, GCP, or live flag activation
- [V5.23 Pre-Execution Authorization Review](docs/V5_23_PRE_EXECUTION_AUTHORIZATION_REVIEW.md) — documentation-only review; 12 sections (A–L plus opening decision block); consolidates Phases 1–4; 4-row phase artifact review (all PASS); 22-control coverage matrix (all PASS); 610 aggregate explicit assertions + smoke 35/35 and 8/8 PASS; 18-category security review (all sensitive categories absent); 17 gaps H-01–H-17 documented (all human/out-of-repo blockers); readiness verdict `READY_TO_PROPOSE`; recommended future authorization path A1-only per-step; explicit forbidden next actions table; even `READY_TO_PROPOSE` does not authorize execution; does not authorize A1–A10, real credentials, OAuth, token exchange, Secret Manager write, Google Ads API, GCP, deploy, or live flag activation
- [V5.23 Branch Closure](docs/V5_23_BRANCH_CLOSURE.md) — READY FOR PHASE 10 AUTHORIZATION; 13 sections (A–M); phase completion matrix Phases 1–5 PASS + Phases 6–8 NOT EXECUTED; 610 aggregate assertions; 24 security confirmations; 17 remaining gaps; 14 NOT APPROVED boundaries; closure decision READY FOR MERGE/TAG/RELEASE AUTHORIZATION ONLY; `READY_TO_PROPOSE` remains not authorization
- [v5.23.0-beta Release Notes](docs/RELEASE_NOTES_V5_23_0_BETA.md) — release candidate `v5.23.0-beta`; 10 sections (A–J); documentation-only release; READY FOR RELEASE (Phase 10 authorization required); Phases 6–8 not executed; 14 NOT APPROVED items; 14 deferred items; does not authorize real OAuth, credentials, token exchange, Secret Manager write, Google Ads API, GCP, deploy, or live flag activation
- [V5.24 Implementation Plan](docs/V5_24_IMPLEMENTATION_PLAN.md) — V5.24 7-phase documentation hardening plan; scope boundary; hardening targets; credential boundary (H-01–H-10); safety envelope (I-01–I-10); deferred items; Phase 7 authorization requirements; does not authorize OAuth, real credentials, Google Ads API, Secret Manager, GCP, deployment, or live flag activation
- [Google Ads Authorization Phrase Validation Protocol](docs/GOOGLE_ADS_AUTHORIZATION_PHRASE_VALIDATION_PROTOCOL.md) — phrase anatomy (8 elements); 15 validity criteria; 30 rejection patterns; 6 response scenarios; channel validation; version/step binding; J-08 phrase non-logging rule; 10 stop conditions; documentation-only; does not authorize A1–A10 or any live step
- [Google Ads Gap Closure Evidence Requirements](docs/GOOGLE_ADS_GAP_CLOSURE_EVIDENCE_REQUIREMENTS.md) — per-gap evidence specs for H-01–H-17; 6 evidence types; 3 sensitivity tiers; sufficiency matrix; evidence expiry; 4 gap clusters; minimum gap set for A1 proposal; documentation-only; all 17 V5.23 gaps remain OPEN
- [Google Ads Ceremony Window Integrity Protocol](docs/GOOGLE_ADS_CEREMONY_WINDOW_INTEGRITY_PROTOCOL.md) — 10 window planning prerequisites; dry-run staleness rules; smoke suite and safety grep currency; window sizing guide; overlap detection; abort/restart protocol; extension prohibition; window integrity verification (open/mid/close); 10 stop conditions; documentation-only; does not authorize any live step
- [V5.24 Hardening Review](docs/V5_24_HARDENING_REVIEW.md) — hardening verdict `HARDENED`; zero contradictions with V5.18–V5.23; 22/22 V5.23 controls PASS (4 strengthened); 610 baseline demo assertions + 211 V5.24 clauses = 821 combined; 18 sensitive categories absent; all 17 gaps OPEN; V5.23 `READY_TO_PROPOSE` unchanged; does not authorize A1–A10 or real execution
- [V5.24 Branch Closure](docs/V5_24_BRANCH_CLOSURE.md) — READY FOR PHASE 7 AUTHORIZATION; Phases 1–6 PASS; `HARDENED` verdict; 25 security confirmations; 14 NOT APPROVED boundaries
- [v5.24.0-beta Release Notes](docs/RELEASE_NOTES_V5_24_0_BETA.md)

## Admin credential configuration (V5.16+)

OpenClaw admin endpoints are scope-gated. Set the following env vars to control access. Use placeholders only — never commit real token values.

| Variable | Scope granted | Purpose |
|----------|--------------|---------|
| `OPENCLAW_ADMIN_KEYS` | `ADMIN` (all operations) | Comma-separated admin-scope tokens; required for WRITE, VALIDATE, ROTATE, DELETE |
| `OPENCLAW_READ_KEYS` | `READ` | Comma-separated read-only tokens |
| `OPENCLAW_API_KEYS` | `READ` (backward-compatible fallback) | Existing API key configurations continue to work as read-only |
| `OPENCLAW_ADMIN_DELETE_ENABLED` | — | Set to `true` to enable `DELETE /credentials/google-ads`; disabled by default |
| `OPENCLAW_AUDIT_RETAIN_DAYS` | — | Audit JSONL retention days for `prune_audit_files()`; default `90` |
| `OPENCLAW_TENANT_KEYS` | `` | Comma-separated `token:tenant_id` pairs; restricts listed tokens to their allowed tenants (V5.17+) |
| `OPENCLAW_ADMIN_RATE_LIMIT_RPM` | `0` | Max requests/min for STANDARD admin routes per token; `0` = disabled (V5.17+) |
| `OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM` | `0` | Max requests/min for SENSITIVE admin routes per token; `0` = disabled (V5.17+) |

Example (local dev only — use placeholder values):

```bash
export OPENCLAW_API_AUTH_ENABLED=true
export OPENCLAW_ADMIN_KEYS=<your-admin-token-here>
export OPENCLAW_READ_KEYS=<your-read-token-here>
```

A valid token with insufficient scope returns `403 scope_not_granted`. A missing or invalid token returns `401 unauthorized`.

## Roadmap summary

| Version | Focus | Status |
|---|---|---|
| V0 | Ads Agent · Router · n8n · Demo Client | **Complete** — `v0.0.1` |
| V1 | LangGraph · stateful analysis | **Complete** — `v1.4.1` |
| V2 | MemPalace · persistent client memory | **Beta complete** — `v2.0.0-beta` |
| V3 | OpenClaw · HTTP API · tenant context · audit log | **Alpha complete** — `v3.0.0-alpha` |
| V3.5 | Config · auth placeholder · CORS · Docker · GCP plan | **Beta complete** — `v3.5.0-beta` |
| V4 | Real integrations · Google Ads API · data source resolver | **Beta complete** — `v4.0.0-beta` |
| V4.5.1 | Live Google Ads read-only fetch · GAQL · credential safety gates | **Alpha** — `v4.5.1-alpha` |
| V5 | Tenant credentials · secure onboarding · secret store · OAuth | **Beta complete** — `v5.0.0-beta` |
| V5.12 | GCP Secret Manager backend · `GCPSecretManagerStore` · IAM · rotation | **Beta complete** — `v5.12.0-beta` |
| V5.13 | Live GCP validation · Phases A–F PASS · provider composition confirmed | **Beta complete** — `v5.13.0-beta` |
| V5.14 | Admin credential bundle GCP wiring · POST endpoint · TestClient smoke · live GCP validation | **Beta complete** — `v5.14.0-beta` |
| V5.15 | Credential lifecycle hardening · audit events · structural validation · revoke/delete endpoint | **Beta complete** — `v5.15.0-beta` |
| V5.16 | Admin RBAC · audit seq/digest · credential rotation endpoint | **Beta complete** — `v5.16.0-beta` |
| V5.17 | Production readiness · tenant isolation · rate limiting · audit locking · operator runbook | **Beta complete** — `v5.17.0-beta` |
| V5.18 | Live GCP fake-secret validation · write → validate → rotate → delete → audit | **Beta complete** — `v5.18.0-beta` |
| V5.19 | Real credential readiness gates · live-mode gate · approval workflow · preflight · guardrails · audit | **Beta complete** — `v5.19.0-beta` |
| V5.20 | Controlled real Google Ads onboarding readiness · ceremony · checklist · intake boundary · first-call plan · rollback drill · version lifecycle policy · final readiness review | **Beta complete** — `v5.20.0-beta` |
| V5.21 | Controlled real Google Ads OAuth onboarding ceremony · authorization URL design · callback boundary · credential handoff protocol · approval packet · dry-run runbook | **Beta complete** — `v5.21.0-beta` |
| V5.22 | Controlled real OAuth ceremony dry run execution · dry-run packet · execution validator · stop/rollback rehearsal · final dry-run review | **Beta complete** — `v5.22.0-beta` |
| V5.23 | Controlled real OAuth execution planning · authorization architecture · per-step approval model · secret/credential boundary · stop conditions · safety envelope | **Beta complete** — `v5.23.0-beta` |
| V5.24 | Documentation and planning hardening · authorization phrase validation · gap closure evidence requirements · ceremony window integrity protocol | **In progress** — `v5.24-documentation-planning-hardening` |
