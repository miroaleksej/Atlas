"""Canonical serialization, content addressing and provenance receipts.

This is the deliberately small descendant of the useful HTCE serialization,
hashing and trace ideas.  No toroidal/scalar arithmetic is used for scientific
quantities.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


TRACE_GENESIS = "00" * 32


class CanonicalizationError(ValueError):
    pass


def _assert_canonical_tree(value: Any, *, path: str = "$", seen: set[int] | None = None) -> None:
    if seen is None:
        seen = set()
    if isinstance(value, (dict, list, tuple)):
        obj_id = id(value)
        if obj_id in seen:
            raise CanonicalizationError(f"cyclic JSON structure at {path}")
        seen.add(obj_id)
        try:
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise CanonicalizationError(f"non-string key at {path}")
                    _assert_canonical_tree(item, path=f"{path}.{key}", seen=seen)
            else:
                for index, item in enumerate(value):
                    _assert_canonical_tree(item, path=f"{path}[{index}]", seen=seen)
        finally:
            seen.remove(obj_id)
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError(f"non-finite float at {path}")
        raise CanonicalizationError(f"float rejected from authoritative digest material at {path}")
    if value is None or isinstance(value, (str, int, bool)):
        return
    raise CanonicalizationError(f"unsupported canonical type {type(value).__name__} at {path}")


def canonical_bytes(value: Any) -> bytes:
    _assert_canonical_tree(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_json(value: Any, *, namespace: bytes) -> str:
    return sha256_hex(namespace + b"\x00" + canonical_bytes(value))


def merkle_root(values: Sequence[Any], *, namespace: bytes) -> str:
    leaves = [hashlib.sha256(namespace + b"\x00leaf\x00" + canonical_bytes(v)).digest() for v in values]
    if not leaves:
        return hashlib.sha256(namespace + b"\x00empty").hexdigest()
    level = leaves
    while len(level) > 1:
        if len(level) % 2:
            level = level + [level[-1]]
        level = [
            hashlib.sha256(namespace + b"\x00node\x00" + level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()


def mapping_root(mapping: Mapping[str, Any], *, namespace: bytes) -> str:
    rows = [{"key": str(k), "value": mapping[k]} for k in sorted(mapping)]
    return merkle_root(rows, namespace=namespace)


@dataclass(frozen=True, slots=True)
class TraceEntry:
    index: int
    previous_digest: str
    event: dict[str, Any]
    digest: str

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "previous_digest": self.previous_digest,
            "event": self.event,
            "digest": self.digest,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "TraceEntry":
        return cls(
            index=int(payload["index"]),
            previous_digest=str(payload["previous_digest"]),
            event=dict(payload["event"]),
            digest=str(payload["digest"]),
        )


@dataclass(frozen=True, slots=True)
class ProvenanceTrace:
    entries: tuple[TraceEntry, ...] = ()

    @property
    def head(self) -> str:
        return TRACE_GENESIS if not self.entries else self.entries[-1].digest

    def append(self, event: Mapping[str, Any]) -> "ProvenanceTrace":
        index = len(self.entries)
        previous = self.head
        event_json = dict(event)
        digest = digest_json(
            {"index": index, "previous_digest": previous, "event": event_json},
            namespace=b"SCIENCEATLAS_AI_TRACE_V1",
        )
        return ProvenanceTrace(self.entries + (TraceEntry(index, previous, event_json, digest),))

    def verify(self) -> bool:
        previous = TRACE_GENESIS
        for index, entry in enumerate(self.entries):
            if entry.index != index or entry.previous_digest != previous:
                return False
            expected = digest_json(
                {"index": index, "previous_digest": previous, "event": entry.event},
                namespace=b"SCIENCEATLAS_AI_TRACE_V1",
            )
            if expected != entry.digest:
                return False
            previous = entry.digest
        return True

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-provenance-trace-v1",
            "entries": [entry.to_json() for entry in self.entries],
            "head": self.head,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ProvenanceTrace":
        trace = cls(tuple(TraceEntry.from_json(row) for row in payload.get("entries", [])))
        if str(payload.get("head", trace.head)) != trace.head or not trace.verify():
            raise ValueError("provenance trace verification failed")
        return trace
