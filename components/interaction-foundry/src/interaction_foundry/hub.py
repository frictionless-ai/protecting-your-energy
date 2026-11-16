"""Explicit private Hugging Face delivery for an already-reviewed release."""

import hashlib
import json
from pathlib import Path
import re


_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_ALLOWED = {"development.jsonl", "validation.jsonl", "test.jsonl", "README.md", "manifest.json"}


def preflight_release(path: str | Path, repo_id: str) -> dict:
    """Validate a local release before network access or repository creation."""
    release = Path(path)
    if not _REPO.fullmatch(repo_id):
        raise ValueError("repo_id must be namespace/name")
    if not release.is_dir() or release.is_symlink():
        raise ValueError("release must be a real directory")
    names = {child.name for child in release.iterdir()}
    if (not names.issubset(_ALLOWED) or "README.md" not in names
            or "manifest.json" not in names or not any(name.endswith(".jsonl") for name in names)):
        raise ValueError("release has unexpected or missing files")
    manifest = json.loads((release / "manifest.json").read_text())
    if set(manifest) != names - {"manifest.json"}:
        raise ValueError("manifest must cover every release payload")
    for name, expected in manifest.items():
        if not isinstance(expected, str) or hashlib.sha256((release / name).read_bytes()).hexdigest() != expected:
            raise ValueError("manifest digest mismatch")
    from .dataset import validate_case
    for name in sorted(names):
        if not name.endswith(".jsonl"):
            continue
        with (release / name).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    case = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSON in {name}:{line_number}") from error
                validate_case(case)
    return {"repo_id": repo_id, "files": sorted(names), "visibility": "private"}


def zapier_delivery_payload(path: str | Path, repo_id: str, *, commit_message: str) -> dict:
    """Build the exact hash-bound payload for the guarded Zapier Hub action.

    This function performs no network request. It first checks the local source
    release, then creates the *remote* manifest after moving split files below
    ``data/``. Callers must pass this object unchanged to the configured
    ``publish_private_evaluation_dataset`` Zapier code action.
    """
    preflight = preflight_release(path, repo_id)
    if not isinstance(commit_message, str) or not commit_message.strip():
        raise ValueError("commit_message is required")
    release = Path(path)
    payloads = {"README.md": (release / "README.md").read_text(encoding="utf-8")}
    for name in preflight["files"]:
        if name.endswith(".jsonl"):
            payloads[f"data/{name}"] = (release / name).read_text(encoding="utf-8")
    remote_manifest = {
        name: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for name, content in sorted(payloads.items())
    }
    payloads["manifest.json"] = json.dumps(remote_manifest, sort_keys=True, indent=2) + "\n"
    files = [
        {"path": name, "utf8_content": content,
         "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
        for name, content in sorted(payloads.items())
    ]
    return {"repo_id": repo_id, "commit_message": commit_message, "files": files,
            "visibility": "private", "local_files": preflight["files"]}


def publish_private(path: str | Path, repo_id: str, *, token: str | None = None) -> dict:
    """Create/replace files in a private dataset repo, then verify remote names.

    Calling this function is an external write. It intentionally has no default
    repository name and rejects any release that has not passed local preflight.
    """
    result = preflight_release(path, repo_id)
    try:
        from huggingface_hub import HfApi
    except ImportError as error:
        raise RuntimeError("install optional dependency: pip install .[hub]") from error
    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(path), path_in_repo="")
    remote = {entry.rfilename for entry in api.list_repo_tree(repo_id, repo_type="dataset", recursive=True)}
    missing = set(result["files"]) - remote
    if missing:
        raise RuntimeError("remote verification missing expected release files")
    return result | {"remote_verified": True}
