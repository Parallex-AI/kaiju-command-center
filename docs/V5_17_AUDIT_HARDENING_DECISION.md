# V5.17 Phase 5 — Audit Persistence Hardening Decision

**Kaiju Command Center — OpenClaw**

---

## 1. Purpose

This document records the design decision for V5.17 Phase 5: hardening the audit JSONL append path against seq/file_digest races introduced by concurrent writers in the same process group.

---

## 2. Current Audit Model (V5.16 Baseline)

OpenClaw writes one JSONL event per admin credential operation to a daily file under `OPENCLAW_AUDIT_ROOT`. Each event carries:

- `seq` — 1-based integer position within the file, computed by counting non-empty lines before append
- `file_digest` — SHA-256 of all file bytes before this append, computed immediately before the write

`verify_audit_file()` in `openclaw/audit_maintenance.py` replays the chain to detect tampered or out-of-order events.

---

## 3. Problem Statement

In V5.16, `seq` and `file_digest` were computed outside any file lock:

```
read file → compute seq + digest → open for append → write
```

If two writers race — for example, two concurrent HTTP requests hitting the same Cloud Run instance — both may read the file at the same state, compute the same seq, and write conflicting lines. `verify_audit_file()` would then report `seq_mismatch` or `digest_mismatch` errors on a file that was never tampered.

This is a correctness gap, not a security breach: the seq/digest chain exists to detect external tampering, not to serve as a hard quota or transaction log.

---

## 4. Options Evaluated

| Option | Description | Decision |
|---|---|---|
| A | JSONL + seq/file_digest only — V5.16 baseline | Baseline; insufficient under concurrent load |
| B | File locking around seq/digest/write (`fcntl.flock LOCK_EX`) | **Selected for V5.17** |
| C | Append-only filesystem permissions (e.g., `chattr +a`) | Operator guidance only; not implemented |
| D | Cloud Storage object archival with object lock | Deferred — requires GCP resource, cost |
| E | BigQuery audit replication | Deferred — cost, IAM complexity |
| F | KMS/HSM cryptographic signing of each event | Deferred — complexity, IAM, latency |

---

## 5. V5.17 Decision

**Implement Option B. Document Option C as operator guidance. Defer D, E, F.**

Option B provides a correct, zero-infrastructure race fix for single-instance deployments. It uses `fcntl.flock(LOCK_EX)` — the standard POSIX advisory file lock — to guarantee that seq computation, digest computation, and the JSONL write are atomic with respect to other writers that also call `flock`.

Option C (append-only inode bit) prevents overwriting but does not protect the seq/digest chain from concurrent writers, so it is guidance, not a replacement for locking.

Options D, E, F require GCP resources, billing authorization, and IAM changes. They are appropriate future milestones and are explicitly out of scope for this phase.

---

## 6. Implementation Summary

**File:** `openclaw/audit.py`

At module import:

```python
try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _fcntl = None
    _HAS_FCNTL = False
```

Modified `append_audit_event()`:

```
if _HAS_FCNTL:
    touch file to ensure it exists
    open(file, "r+b")
    flock(LOCK_EX)
    read all current bytes
    compute file_digest from current bytes
    compute seq from current byte count
    stamp event["seq"] and event["file_digest"]
    seek to end
    write encoded JSONL line
    flush
    flock(LOCK_UN)
    lock_used = True
else:
    # fallback: existing behavior, no locking
    compute digest and seq from file
    open(file, "a")
    write JSONL line
    lock_used = False

return {"ok": True, ..., "lock_used": lock_used}
```

The `lock_used` field in the return value allows callers and tests to confirm whether locking was applied. All existing callers that only check `result.get("ok")` remain fully compatible.

Audit failure remains non-fatal: any exception in `append_audit_event()` returns `{"ok": False, "error": "<ExceptionClassName>"}` and the credential operation continues with `warnings=["audit_append_failed"]`.

---

## 7. Limitations

- **Unix-only.** `fcntl` is not available on Windows. The fallback path (no lock) is used automatically. This is acceptable because Cloud Run runs Linux containers.
- **Advisory lock only.** `fcntl.flock` does not prevent a privileged process or direct filesystem access from writing to the audit file outside the locking protocol. It prevents races between cooperative writers in the same process group.
- **Not cryptographic.** The seq/file_digest chain is tamper-evident, not cryptographically signed. A privileged attacker with write access to the audit file can rewrite the chain consistently. Option F (KMS signing) addresses this but is deferred.
- **Process-local state only.** The lock serializes writers within one process. If multiple Cloud Run instances write to different local filesystem paths (ephemeral container storage), there is no cross-instance lock and each instance maintains a separate audit chain. This is a known architectural constraint of local-file audit logging.
- **Not durable across instance restarts.** Cloud Run container filesystems are ephemeral. Local audit files are lost on instance restart. External archival (Option D or E) is required for durable long-term retention. This is a known limitation of the current design.
- **`verify_audit_file()` is unchanged.** It verifies the chain as written; it does not audit the audit writer itself.

---

## 8. Future Options

| Option | What it adds | Pre-requisite |
|---|---|---|
| D — Cloud Storage archival | Durable, cross-instance audit log with optional object lock | GCP project, bucket, IAM `roles/storage.objectAdmin` |
| E — BigQuery replication | Queryable audit history, cross-instance | GCP project, dataset, IAM `roles/bigquery.dataEditor`, billing |
| F — KMS signing | Cryptographic proof of event integrity | GCP KMS key, IAM `roles/cloudkms.signerVerifier` |
| C — `chattr +a` | Filesystem-level append protection | Operator action, Linux only, does not fix seq/digest race |

None of these are implemented in V5.17. All require explicit operator authorization and billing approval before work begins.

---

## 9. Non-Goals

This phase does **not**:

- Create any GCP resource
- Require any IAM change
- Introduce Redis, Memorystore, Cloud Storage, or any external service
- Add BigQuery replication
- Implement KMS/HSM signing
- Deploy to Cloud Run
- Enable `GOOGLE_ADS_LIVE_ENABLED=true`

---

## 10. Test Coverage

| Test | Location |
|---|---|
| `_HAS_FCNTL` importable from `audit` | `scripts/smoke_test_v5_credentials.sh` [20/20] |
| `LOCK_EX` present in `audit.py` | `scripts/smoke_test_v5_credentials.sh` [20/20] |
| `append_audit_event` returns `lock_used`, `seq=1` | `scripts/smoke_test_v5_credentials.sh` [20/20] |
| Section U: two appends, seq increments, `verify_audit_file` ok | `openclaw/run_admin_credentials_lifecycle_demo.py` Section U |
| Section U: no forbidden fields in lock section events | `openclaw/run_admin_credentials_lifecycle_demo.py` Section U |
| Section U pass confirmed in smoke | `scripts/smoke_test_v5_credentials.sh` [20/20] |

All tests run locally. No GCP resource required.

---

## 11. Related Documents

- `docs/CREDENTIAL_LIFECYCLE_RUNBOOK.md` — Section 12: Audit Verification (updated in V5.17 Phase 5)
- `docs/V5_17_RATE_LIMITING_DESIGN.md` — V5.17 Phase 4: rate limiting design
- `docs/V5_17_PER_TENANT_PERMISSION_DESIGN.md` — V5.17 Phase 3: per-tenant token isolation
- `openclaw/audit.py` — Implementation
- `openclaw/audit_maintenance.py` — `verify_audit_file()`, `prune_audit_files()`
