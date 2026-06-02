"""
V5.4 — LocalFileCredentialReferenceStore.

Defines:
- get_default_credential_reference_store_path: CREDENTIAL_REFERENCE_STORE_PATH env var or
  repo-root default (runtime/credential-references/credential_references.json)
- load_reference_store_file: load JSON from disk; missing file → empty store
- write_reference_store_file: atomic write via tempfile + os.replace
- dict_to_credential_reference: deserialize stored dict to validated CredentialReference
- LocalFileCredentialReferenceStore: file-backed CredentialStore implementation

WARNING: This is a REFERENCE store, not a secret store.
Secret material (developer_token, client_secret, refresh_token, access_token, OAuth codes)
must never be written to this file. Use GCP Secret Manager or equivalent for secrets.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from credentials.models import (
    CredentialReference,
    CredentialStatus,
    credential_reference_to_dict,
    credential_reference_to_redacted_response,
    update_credential_status,
    validate_credential_reference,
)
from credentials.store import (
    CredentialStore,
    assert_no_secret_material,
    make_store_key,
    missing_credential_status,
)

_ENV_VAR = "CREDENTIAL_REFERENCE_STORE_PATH"
_STORE_VERSION = 1


def get_default_credential_reference_store_path() -> Path:
    """
    Return the credential reference store file path.

    Reads CREDENTIAL_REFERENCE_STORE_PATH env var if set.
    Otherwise returns runtime/credential-references/credential_references.json
    anchored at the repo root (3 parents up from this file's directory).
    """
    env_val = os.environ.get(_ENV_VAR, "").strip()
    if env_val:
        return Path(env_val)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "runtime" / "credential-references" / "credential_references.json"


def _empty_store() -> dict:
    return {"version": _STORE_VERSION, "references": {}}


def load_reference_store_file(path: Union[str, Path, None] = None) -> dict:
    """
    Load the JSON reference store from disk.

    - Missing file: returns empty store structure (version + empty references dict).
    - Invalid JSON or unexpected structure: raises ValueError with a safe message.
    - Never logs file contents.
    """
    target = Path(path) if path is not None else get_default_credential_reference_store_path()
    if not target.exists():
        return _empty_store()
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Failed to read credential reference store: {exc.strerror}"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Credential reference store contains invalid JSON ({target.name}): {exc.msg}"
        ) from exc
    if not isinstance(data, dict) or "references" not in data:
        raise ValueError(
            "Credential reference store has unexpected structure — expected 'references' key"
        )
    if not isinstance(data["references"], dict):
        raise ValueError(
            "Credential reference store 'references' value must be a dict"
        )
    return data


def write_reference_store_file(
    payload: dict,
    path: Union[str, Path, None] = None,
) -> None:
    """
    Write the store dict to disk atomically.

    Creates the parent directory if needed.
    Writes to a temp file first, then uses os.replace for atomic POSIX replacement.
    Raises ValueError with a safe message on I/O failure.
    """
    target = Path(path) if path is not None else get_default_credential_reference_store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, target)
    except Exception as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise ValueError(f"Failed to write credential reference store: {exc}") from exc


def dict_to_credential_reference(payload: dict) -> CredentialReference:
    """
    Deserialize a stored dict to a validated CredentialReference.

    Raises ValueError if:
    - The dict cannot be converted to CredentialReference
    - The resulting reference fails validate_credential_reference
    - The metadata contains any secret-like key names
    """
    try:
        ref = CredentialReference(
            tenant_id=payload.get("tenant_id", ""),
            client_id=payload.get("client_id", ""),
            integration_type=payload.get("integration_type", ""),
            credential_ref=payload.get("credential_ref", ""),
            customer_id=payload.get("customer_id"),
            login_customer_id=payload.get("login_customer_id"),
            status=payload.get("status", CredentialStatus.MISSING.value),
            last_validated_at=payload.get("last_validated_at"),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            metadata=payload.get("metadata") or None,
        )
    except (TypeError, KeyError) as exc:
        raise ValueError(
            f"Cannot deserialize stored credential reference: {exc}"
        ) from exc
    valid, errors = validate_credential_reference(ref)
    if not valid:
        safe_fields = [e.get("field", "unknown") for e in errors]
        raise ValueError(
            f"Stored credential reference is invalid — fields: {safe_fields}"
        )
    if ref.metadata:
        clean, offending = assert_no_secret_material(ref.metadata)
        if not clean:
            raise ValueError(
                f"Stored reference metadata contains secret-like keys: {offending}"
            )
    return ref


class LocalFileCredentialReferenceStore(CredentialStore):
    """
    File-backed CredentialReference store for local development and testing.

    Persists CredentialReference metadata to a JSON file.
    Uses atomic writes (tempfile + os.replace) to prevent partial writes on crash.

    WARNING: This is a REFERENCE store, not a secret store.
    Secret material (developer_token, client_secret, refresh_token, access_token,
    OAuth codes) must never be written here. Actual secrets belong in a SecretStore
    (GCP Secret Manager, etc.), which is deferred to a future V5 phase.

    Not suitable for concurrent multi-process access.
    Not suitable for production multi-tenant deployments.
    """

    def __init__(self, path: Union[str, Path, None] = None) -> None:
        self._path: Path = (
            Path(path) if path is not None
            else get_default_credential_reference_store_path()
        )

    @property
    def store_path(self) -> Path:
        """The resolved path to the JSON store file."""
        return self._path

    def put_reference(self, ref: CredentialReference) -> CredentialReference:
        valid, errors = validate_credential_reference(ref)
        if not valid:
            safe_codes = [e.get("code", "invalid") for e in errors]
            safe_fields = [e.get("field", "unknown") for e in errors]
            raise ValueError(
                f"CredentialReference is invalid — codes: {safe_codes}, fields: {safe_fields}"
            )
        if ref.metadata:
            clean, offending = assert_no_secret_material(ref.metadata)
            if not clean:
                raise ValueError(
                    f"CredentialReference metadata contains secret-like keys: {offending}"
                )
        store = load_reference_store_file(self._path)
        key = make_store_key(ref.tenant_id, ref.client_id, ref.integration_type)
        store["references"][key] = credential_reference_to_dict(ref)
        write_reference_store_file(store, self._path)
        return ref

    def get_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> Optional[CredentialReference]:
        store = load_reference_store_file(self._path)
        key = make_store_key(tenant_id, client_id, integration_type)
        raw = store["references"].get(key)
        if raw is None:
            return None
        return dict_to_credential_reference(raw)

    def get_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> dict:
        ref = self.get_reference(tenant_id, client_id, integration_type)
        if ref is None:
            return missing_credential_status(tenant_id, client_id, integration_type)
        return credential_reference_to_redacted_response(ref)

    def update_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
        status: str,
        last_validated_at: Optional[str] = None,
    ) -> Optional[CredentialReference]:
        store = load_reference_store_file(self._path)
        key = make_store_key(tenant_id, client_id, integration_type)
        raw = store["references"].get(key)
        if raw is None:
            return None
        ref = dict_to_credential_reference(raw)
        updated = update_credential_status(ref, status, last_validated_at)
        store["references"][key] = credential_reference_to_dict(updated)
        write_reference_store_file(store, self._path)
        return updated

    def delete_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> bool:
        store = load_reference_store_file(self._path)
        key = make_store_key(tenant_id, client_id, integration_type)
        if key not in store["references"]:
            return False
        del store["references"][key]
        write_reference_store_file(store, self._path)
        return True

    def list_references(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[CredentialReference]:
        store = load_reference_store_file(self._path)
        refs = []
        for raw in store["references"].values():
            try:
                ref = dict_to_credential_reference(raw)
            except ValueError:
                continue
            if tenant_id is None or ref.tenant_id == tenant_id:
                refs.append(ref)
        return refs
