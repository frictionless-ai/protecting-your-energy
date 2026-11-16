"""Load explicit private account attribution; never infer it from display names."""

import json
from pathlib import Path
import re


_ACCOUNT_ID = re.compile(r"^\d{17,20}$")
_BASES = {"authenticated_export_metadata", "user_verified"}


def load_verified_discord_accounts(path: str | Path) -> frozenset[str]:
    """Return explicitly attested Discord IDs from ignored private storage.

    The file is intentionally separate from source exports. A caller still
    needs reply/reaction/date evidence before claiming social reception.
    """
    data = json.loads(Path(path).read_text())
    required = {"schema", "verification_basis", "discord_account_ids"}
    if not isinstance(data, dict) or set(data) != required or data["schema"] != "interaction-foundry/private-identity/v1":
        raise ValueError("invalid private identity attestation")
    if data["verification_basis"] not in _BASES:
        raise ValueError("identity verification basis is required")
    ids = data["discord_account_ids"]
    if not isinstance(ids, list) or not ids or any(not isinstance(value, str) or not _ACCOUNT_ID.fullmatch(value) for value in ids):
        raise ValueError("discord account IDs must be stable numeric identifiers")
    if len(ids) != len(set(ids)):
        raise ValueError("discord account IDs must be unique")
    return frozenset(ids)
