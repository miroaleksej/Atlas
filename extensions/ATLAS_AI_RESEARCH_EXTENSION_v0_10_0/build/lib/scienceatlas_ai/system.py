"""Composite persistent system: runtime + continual learning + closed loop.

``ScienceAtlasAI.snapshot_root()`` covers only the runtime's own components, and
``persistence.py`` seals exactly that.  Anything added outside it, including
genesis certificates, the alpha ledger, regional strategy scores and loop state,
would be invisible to the root: freeze and replay would keep passing while
silently guaranteeing less than before.

So this module does not widen the runtime root.  It seals a *composite* root
over the runtime root plus each extension component, which keeps the runtime
file untouched and still makes every authoritative addition part of the sealed
identity.

Restore order matters and is fixed: runtime first, extension state second,
rehydration third, verification last.  Rehydration attaches live synthesised
owners over the ``DetachedOwner`` placeholders the runtime installed; it changes
which objects the bus holds, never which specs, so the runtime root is identical
before and after and is re-verified afterwards.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .continual import GenesisState, RegionalMetaLearner
from .provenance import canonical_bytes, digest_json, mapping_root, sha256_hex
from .research_loop import LoopBudget, LoopState, ResearchLoopOwner
from .permutation_eprocess import PermutationEProcessOwner, PermutationEProcessState
from .runtime import ScienceAtlasAI


SYSTEM_SCHEMA = "scienceatlas-ai-system-envelope-v2"
LEGACY_SYSTEM_SCHEMAS = {"scienceatlas-ai-system-envelope-v1", SYSTEM_SCHEMA}


@dataclass
class ResearchSystem:
    ai: ScienceAtlasAI
    meta: RegionalMetaLearner = field(default_factory=RegionalMetaLearner)
    genesis: GenesisState = field(default_factory=GenesisState)
    loop_state: LoopState = field(default_factory=LoopState)
    loop_budget: LoopBudget = field(default_factory=LoopBudget)
    eprocess: PermutationEProcessState = field(default_factory=PermutationEProcessState)

    # -- identity ----------------------------------------------------------

    def extension_components(self) -> dict[str, Any]:
        return {
            "regional_meta": self.meta.to_json(),
            "genesis": self.genesis.to_json(),
            "loop_state": self.loop_state.to_json(),
            "loop_budget": self.loop_budget.to_json(),
            "permutation_eprocess": self.eprocess.to_json(),
        }

    def composite_root(self) -> str:
        roots = {
            name: digest_json(payload, namespace=f"SCIENCEATLAS_AI_EXT_{name.upper()}_V1".encode("ascii"))
            for name, payload in self.extension_components().items()
        }
        roots["runtime_snapshot_root"] = self.ai.snapshot_root()
        return mapping_root(roots, namespace=b"SCIENCEATLAS_AI_SYSTEM_ROOT_V1")

    def loop(self, *, regime_of: Any = None) -> ResearchLoopOwner:
        return ResearchLoopOwner(budget=self.loop_budget, regime_of=regime_of)

    def eprocess_owner(self) -> PermutationEProcessOwner:
        """Live owner over the persistent per-target e-process state."""
        return PermutationEProcessOwner(state=self.eprocess)

    def status(self) -> dict[str, Any]:
        payload = {
            "schema": "scienceatlas-ai-system-status-v1",
            "runtime_version": self.ai.VERSION,
            "composite_root": self.composite_root(),
            "runtime_snapshot_root": self.ai.snapshot_root(),
            "owners": len(self.ai.owner_bus.specs()),
            "observations": len(self.ai.world.observations),
            "loop_step": self.loop_state.step,
            "loop_acquisitions": self.loop_state.acquisitions,
            "retired_targets": sorted(self.loop_state.exhausted),
            "synthesized_active": list(self.genesis.active_owner_ids()),
            "synthesized_revoked": list(self.genesis.revoked_owner_ids),
            "alpha_balance_bp": self.genesis.ledger.balance_bp,
            "eprocess_epoch_records": len(self.eprocess.records),
            "eprocess_global_online_controller": "UNIMPLEMENTED",
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_SYSTEM_STATUS_V1")
        return payload

    # -- persistence -------------------------------------------------------

    def to_envelope(self, *, code_digest: str | None = None, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
        runtime_state = self.ai.to_json()
        extension = self.extension_components()
        manifest = {
            "schema": "scienceatlas-ai-system-manifest-v2",
            "version": self.ai.VERSION,
            "composite_root": self.composite_root(),
            "runtime_snapshot_root": str(runtime_state["snapshot_root"]),
            "runtime_state_digest": sha256_hex(canonical_bytes(dict(runtime_state))),
            "extension_digest": sha256_hex(canonical_bytes(extension)),
            "trace_head": str(runtime_state["trace"]["head"]),
            "code_digest": str(code_digest or self.ai.runtime_contract_digest),
            "config_digest": digest_json(dict(config or {}), namespace=b"SCIENCEATLAS_AI_CONFIG_V1"),
        }
        manifest["manifest_root"] = digest_json(manifest, namespace=b"SCIENCEATLAS_AI_SYSTEM_MANIFEST_V2")
        return {"schema": SYSTEM_SCHEMA, "runtime": runtime_state, "extension": extension, "manifest": manifest}

    def save(
        self,
        path: str | Path,
        *,
        code_digest: str | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = canonical_bytes(self.to_envelope(code_digest=code_digest, config=config))
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
        return target

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        expected_code_digest: str | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> tuple["ResearchSystem", dict[str, Any]]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema") not in LEGACY_SYSTEM_SCHEMAS:
            raise ValueError("unsupported system envelope")
        runtime_state = dict(payload["runtime"])
        extension = dict(payload["extension"])
        manifest = dict(payload["manifest"])

        supplied_root = str(manifest.pop("manifest_root", ""))
        manifest_schema = str(manifest.get("schema", ""))
        manifest_ns = (b"SCIENCEATLAS_AI_SYSTEM_MANIFEST_V1" if manifest_schema == "scienceatlas-ai-system-manifest-v1"
                       else b"SCIENCEATLAS_AI_SYSTEM_MANIFEST_V2")
        if supplied_root != digest_json(manifest, namespace=manifest_ns):
            raise ValueError("system manifest root mismatch")
        if sha256_hex(canonical_bytes(runtime_state)) != str(manifest.get("runtime_state_digest", "")):
            raise ValueError("runtime state digest mismatch")
        if sha256_hex(canonical_bytes(extension)) != str(manifest.get("extension_digest", "")):
            raise ValueError("extension digest mismatch")
        config_digest = digest_json(dict(config or {}), namespace=b"SCIENCEATLAS_AI_CONFIG_V1")
        if config_digest != str(manifest.get("config_digest", "")):
            raise ValueError("configuration digest mismatch")
        if expected_code_digest is not None and str(manifest.get("code_digest", "")) != expected_code_digest:
            raise ValueError("code digest mismatch")

        # 1. runtime
        ai = ScienceAtlasAI.from_json(runtime_state)
        # 2. extension state
        system = cls(
            ai=ai,
            meta=RegionalMetaLearner.from_json(extension.get("regional_meta", {})),
            genesis=GenesisState.from_json(extension.get("genesis", {})),
            loop_state=LoopState.from_json(extension.get("loop_state", {})),
            loop_budget=LoopBudget(**{
                k: v for k, v in extension.get("loop_budget", {}).items()
                if k not in {"schema"}
            }),
            eprocess=PermutationEProcessState.from_json(extension.get("permutation_eprocess", {})),
        )
        # 3. rehydration of synthesised owners
        rehydration = system.genesis.rehydrate(ai.owner_bus)
        # 4. verification, after rehydration
        if ai.snapshot_root() != str(manifest.get("runtime_snapshot_root", "")):
            raise ValueError("runtime snapshot root changed during restore")
        if system.composite_root() != str(manifest.get("composite_root", "")):
            raise ValueError("composite system root mismatch")
        return (system, rehydration)


__all__ = ["ResearchSystem", "SYSTEM_SCHEMA"]
