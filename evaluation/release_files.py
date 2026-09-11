"""Shared closed-world exclusions for release controls and audits."""
from __future__ import annotations

from pathlib import Path


LOCAL_DIRECTORY_NAMES = frozenset({
    ".git",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "__pycache__",
    "node_modules",
    "dns_snapshots",
})
LOCAL_FILE_NAMES = frozenset({
    ".DS_Store",
    "NAVIER_STOKES_BLIND_EXPERIMENT_CURRENT.json",
    "NAVIER_STOKES_PRIMITIVE_FIELD_CURRENT.json",
    "NAVIER_STOKES_OPERATOR_LANGUAGE_INVENTION_CURRENT.json",
    "HIDDEN_TERM_RESIDUAL_DISCOVERY_CURRENT.json",
    "HIDDEN_TERM_RESIDUAL_DISCOVERY_PROVENANCE_SEAL_REFERENCE_PASS.json",
    "TURBULENCE_DNS_CLOSURE_CURRENT.json",
    "turbulence_dns_closure_manifest.real.json",
})
LOCAL_SUFFIXES = frozenset({".pyc", ".pyo"})


def is_local_artifact(path: Path, root: Path) -> bool:
    """Return true for environment/build artifacts outside the release seal."""
    relative = path.relative_to(root)
    return bool(
        any(part in LOCAL_DIRECTORY_NAMES or part.endswith(".egg-info") for part in relative.parts)
        or relative.name in LOCAL_FILE_NAMES
        or relative.suffix in LOCAL_SUFFIXES
    )
