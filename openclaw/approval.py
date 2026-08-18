"""
V5.19 Phase 3 — Approval record model and local approval store.

Pure local logic. No GCP calls. No Google Ads API calls.
No secrets, tokens, credential values, or resource paths in approval records.
Approval records are scoped to a specific tenant/client pair and integration type.
Claude Code does not self-approve.
"""

import datetime
import json
import os
import re
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

# ---------------------------------------------------------------------------
# Status / Scope constants
# ---------------------------------------------------------------------------

class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    EXPIRED = "expired"
    REJECTED = "rejected"


class ApprovalScope:
    GOOGLE_ADS_LIVE_VALIDATION = "google_ads_live_validation"
    GOOGLE_ADS_CREDENTIAL_ONBOARDING = "google_ads_credential_onboarding"
    GOOGLE_ADS_CREDENTIAL_ROTATION = "google_ads_credential_rotation"
    GOOGLE_ADS_CREDENTIAL_REVOKE = "google_ads_credential_revoke"

# ---------------------------------------------------------------------------
# Forbidden field and value constraints
# ---------------------------------------------------------------------------

_FORBIDDEN_FIELD_NAMES: frozenset = frozenset({
    "credential_ref",
    "secret_id",
    "developer_token",
    "client_secret",
    "refresh_token",
    "access_token",
    "customer_id",
    "login_customer_id",
    "google_ads_client_id",
})

_FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]{5,}"),           # OAuth access tokens
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"),            # OpenAI-style API keys
    re.compile(r"\bprojects/[a-zA-Z0-9\-_]+/"),         # GCP resource paths
    re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email-like values
    re.compile(r"(?:/home/|/root/|/Users/)"),            # local home directory paths
    re.compile(r"fake-v51[89]"),                         # fake payload sentinels
]

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRecord:
    approval_id: str
    tenant_id: str
    client_id: str
    integration_type: str
    scope: str
    status: str
    operator_label: str
    reason: str
    created_at: str
    rollback_plan: str
    expires_at: Optional[str] = None
    approved_at: Optional[str] = None
    revoked_at: Optional[str] = None
    evidence: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ApprovalValidationResult:
    valid: bool
    error_codes: List[str]
    warnings: List[str]

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _check_dict_for_forbidden(d: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key, value in d.items():
        if key.lower() in _FORBIDDEN_FIELD_NAMES:
            errors.append("evidence_metadata_forbidden_field")
        if isinstance(value, str):
            for pattern in _FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    errors.append("evidence_metadata_forbidden_value_pattern")
                    break
    return errors


def _utcnow_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def create_approval_record(
    tenant_id: str,
    client_id: str,
    integration_type: str,
    scope: str,
    operator_label: str,
    reason: str,
    rollback_plan: str,
    status: str = ApprovalStatus.PENDING,
    expires_at: Optional[str] = None,
    evidence: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> ApprovalRecord:
    now = _utcnow_iso()
    return ApprovalRecord(
        approval_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        client_id=client_id,
        integration_type=integration_type,
        scope=scope,
        status=status,
        operator_label=operator_label,
        reason=reason,
        created_at=now,
        rollback_plan=rollback_plan,
        expires_at=expires_at,
        approved_at=now if status == ApprovalStatus.APPROVED else None,
        revoked_at=None,
        evidence=dict(evidence) if evidence else {},
        metadata=dict(metadata) if metadata else {},
    )


def validate_approval_record(
    record: ApprovalRecord,
    now: Optional[str] = None,
) -> ApprovalValidationResult:
    """
    Validate an approval record for correctness and safety.

    Does not check tenant/client/scope/integration_type matching — callers
    that need those checks should use is_approval_valid().
    """
    errors: List[str] = []
    warnings: List[str] = []

    if record.status != ApprovalStatus.APPROVED:
        errors.append(f"approval_not_approved:{record.status}")

    if not record.operator_label.strip():
        errors.append("operator_label_missing")

    if not record.reason.strip():
        errors.append("reason_missing")

    if not record.rollback_plan.strip():
        errors.append("rollback_plan_missing")

    if not record.approved_at:
        errors.append("approved_at_missing")

    if record.expires_at:
        _now = now or _utcnow_iso()
        if _now >= record.expires_at:
            errors.append("approval_expired")

    errors.extend(_check_dict_for_forbidden(record.evidence))
    errors.extend(_check_dict_for_forbidden(record.metadata))

    return ApprovalValidationResult(
        valid=len(errors) == 0,
        error_codes=errors,
        warnings=warnings,
    )


def is_approval_valid(
    record: ApprovalRecord,
    required_scope: str,
    tenant_id: str,
    client_id: str,
    integration_type: str,
    now: Optional[str] = None,
) -> bool:
    """
    Return True only if the record is fully valid AND matches the required context.

    Scope, tenant_id, client_id, and integration_type must all match exactly.
    """
    result = validate_approval_record(record, now=now)
    if not result.valid:
        return False
    if record.scope != required_scope:
        return False
    if record.tenant_id != tenant_id:
        return False
    if record.client_id != client_id:
        return False
    if record.integration_type != integration_type:
        return False
    return True


def sanitize_approval_record(record: ApprovalRecord) -> Dict[str, Any]:
    """
    Return a dict representation of the record with forbidden field names
    removed from evidence and metadata. Safe for storage and logging.
    """
    return {
        "approval_id": record.approval_id,
        "tenant_id": record.tenant_id,
        "client_id": record.client_id,
        "integration_type": record.integration_type,
        "scope": record.scope,
        "status": record.status,
        "operator_label": record.operator_label,
        "reason": record.reason,
        "created_at": record.created_at,
        "rollback_plan": record.rollback_plan,
        "expires_at": record.expires_at,
        "approved_at": record.approved_at,
        "revoked_at": record.revoked_at,
        "evidence": {
            k: v for k, v in record.evidence.items()
            if k.lower() not in _FORBIDDEN_FIELD_NAMES
        },
        "metadata": {
            k: v for k, v in record.metadata.items()
            if k.lower() not in _FORBIDDEN_FIELD_NAMES
        },
    }

# ---------------------------------------------------------------------------
# ApprovalStore abstraction
# ---------------------------------------------------------------------------

class ApprovalStore:
    def put(self, record: ApprovalRecord) -> None:
        raise NotImplementedError

    def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        raise NotImplementedError

    def list_for_client(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: Optional[str] = None,
    ) -> List[ApprovalRecord]:
        raise NotImplementedError

    def revoke(
        self,
        approval_id: str,
        reason: str,
        revoked_at: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

# ---------------------------------------------------------------------------
# LocalFileApprovalStore
# ---------------------------------------------------------------------------

class LocalFileApprovalStore(ApprovalStore):
    """
    Filesystem-backed approval store for development and testing.

    Stores records as a JSON dict keyed by approval_id.
    Writes are atomic via tempfile + rename on the same filesystem.
    Path must be supplied explicitly — no default inside repo.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self._path.exists():
            return {}
        text = self._path.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else {}

    def _save(self, data: Dict[str, Dict[str, Any]]) -> None:
        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent,
            suffix=".tmp",
            prefix="approval_store_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.rename(tmp_path, str(self._path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def put(self, record: ApprovalRecord) -> None:
        data = self._load()
        data[record.approval_id] = sanitize_approval_record(record)
        self._save(data)

    def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        data = self._load()
        raw = data.get(approval_id)
        if raw is None:
            return None
        return ApprovalRecord(**raw)

    def list_for_client(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: Optional[str] = None,
    ) -> List[ApprovalRecord]:
        data = self._load()
        results: List[ApprovalRecord] = []
        for raw in data.values():
            if raw.get("tenant_id") != tenant_id or raw.get("client_id") != client_id:
                continue
            if integration_type is not None and raw.get("integration_type") != integration_type:
                continue
            results.append(ApprovalRecord(**raw))
        return results

    def revoke(
        self,
        approval_id: str,
        reason: str,
        revoked_at: Optional[str] = None,
    ) -> bool:
        data = self._load()
        if approval_id not in data:
            return False
        data[approval_id]["status"] = ApprovalStatus.REVOKED
        data[approval_id]["revoked_at"] = revoked_at or _utcnow_iso()
        data[approval_id]["reason"] = reason
        self._save(data)
        return True
