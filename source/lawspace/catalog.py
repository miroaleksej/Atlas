"""Sparse scientific-cell catalog and canonical owner registry."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from .domains import DOMAIN_REGISTRIES
from .schema import CellOccupancy, LawPassport, ProjectionRecord, canonical_json, digest_payload


class LawCatalog:
    def __init__(self) -> None:
        self.passports: Dict[str, LawPassport] = {}
        self.cells: Dict[str, CellOccupancy] = {}
        self.owner_to_cell: Dict[str, str] = {}
        self.projections: Dict[str, ProjectionRecord] = {}
        # Qualified owner→axis bindings are an ontology overlay, not new passports.
        self.owner_axis_bindings: Dict[str, set[str]] = {}

    @staticmethod
    def cell_id(domain_id: str, coordinates: Mapping[str, Any]) -> str:
        registry = DOMAIN_REGISTRIES[domain_id]
        payload = {
            "schema": registry.schema_version,
            "domain": domain_id,
            "coordinates": {k: coordinates[k] for k in sorted(coordinates)},
        }
        return "CELL-" + digest_payload(payload)[:16].upper()

    def add_passport(self, passport: LawPassport) -> None:
        if passport.owner_id in self.passports:
            raise ValueError(f"duplicate canonical owner {passport.owner_id}")
        if passport.domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain {passport.domain_id}")
        registry = DOMAIN_REGISTRIES[passport.domain_id]
        registry.validate_coordinate(passport.scientific_coordinate)
        expected_cell = self.cell_id(passport.domain_id, passport.scientific_coordinate)
        if passport.home_cell_id != expected_cell:
            raise ValueError(f"{passport.owner_id}: home-cell mismatch {passport.home_cell_id} != {expected_cell}")
        if passport.owner_id in self.owner_to_cell:
            raise ValueError(f"owner already assigned to home-cell: {passport.owner_id}")
        old = self.cells.get(expected_cell)
        occupants = tuple(sorted(set((old.occupant_owner_ids if old else ()) + (passport.owner_id,))))
        self.cells[expected_cell] = CellOccupancy(expected_cell, passport.domain_id, dict(passport.scientific_coordinate), occupants, registry.digest)
        self.passports[passport.owner_id] = passport
        self.owner_to_cell[passport.owner_id] = expected_cell

    def add_owner_axis_binding(self, owner_id: str, axis_fq: str) -> None:
        owner_id = str(owner_id).strip()
        axis_fq = str(axis_fq).strip()
        if owner_id not in self.passports:
            raise ValueError(f"owner-axis binding references unknown owner: {owner_id}")
        if "." not in axis_fq:
            raise ValueError(f"owner-axis binding requires fully-qualified axis: {axis_fq}")
        domain_id, axis_id = axis_fq.split(".", 1)
        passport = self.passports[owner_id]
        if domain_id != passport.domain_id:
            raise ValueError(f"owner-axis binding crosses owner domain without a bridge: {owner_id} -> {axis_fq}")
        registry = DOMAIN_REGISTRIES.get(domain_id)
        if registry is None or axis_id not in registry.axes:
            raise ValueError(f"owner-axis binding references unknown canonical axis: {axis_fq}")
        self.owner_axis_bindings.setdefault(owner_id, set()).add(axis_fq)

    def effective_owner_axis_bindings(self, owner_id: str) -> tuple[str, ...]:
        passport = self.passports[owner_id]
        registry = DOMAIN_REGISTRIES[passport.domain_id]
        direct = {
            f"{passport.domain_id}.{axis_id}"
            for axis_id, value in passport.scientific_coordinate.items()
            if axis_id in registry.axes and value not in (None, "", (), [], {})
        }
        return tuple(sorted(direct | set(self.owner_axis_bindings.get(owner_id, set()))))

    def add_projection(self, projection: ProjectionRecord) -> None:
        if projection.projection_id in self.projections:
            raise ValueError(f"duplicate projection {projection.projection_id}")
        if projection.source_owner_id not in self.passports:
            raise ValueError(f"projection source owner not registered: {projection.source_owner_id}")
        if projection.target_cell_id not in self.cells:
            raise ValueError(f"projection target cell not registered: {projection.target_cell_id}")
        if not projection.transformation.canonical:
            raise ValueError("projection requires an exact transformation expression")
        self.projections[projection.projection_id] = projection

    def search(self, query: str, *, domain_id: str | None = None, limit: int = 20) -> List[LawPassport]:
        tokens = [t.casefold() for t in query.split() if t.strip()]
        ranked: List[Tuple[int, str, LawPassport]] = []
        for passport in self.passports.values():
            if domain_id and passport.domain_id != domain_id:
                continue
            haystack = " ".join((passport.owner_id, passport.name_ru, passport.formula.source, passport.domain_id)).casefold()
            score = sum(3 if token in passport.name_ru.casefold() else 1 for token in tokens if token in haystack)
            if not tokens or score:
                ranked.append((-score, passport.owner_id, passport))
        return [row[2] for row in sorted(ranked)[: max(0, limit)]]

    def find_by_dimensions(self, dimension_vector: Sequence[str]) -> List[LawPassport]:
        target = tuple(str(v) for v in dimension_vector)
        result = []
        for passport in self.passports.values():
            vectors = passport.quantity_semantics.get("dimension_vectors", [])
            if any(tuple(str(v) for v in vector) == target for vector in vectors if isinstance(vector, (list, tuple))):
                result.append(passport)
        return sorted(result, key=lambda p: p.owner_id)

    def get_passport(self, owner_id: str) -> LawPassport:
        return self.passports[owner_id]

    def find_home_cell(self, owner_id: str) -> CellOccupancy:
        return self.cells[self.owner_to_cell[owner_id]]

    def digest(self) -> str:
        payload = {
            "passports": {k: asdict(v) for k, v in sorted(self.passports.items())},
            "cells": {k: asdict(v) for k, v in sorted(self.cells.items())},
            "projections": {k: asdict(v) for k, v in sorted(self.projections.items())},
            "owner_axis_bindings": {k: sorted(v) for k, v in sorted(self.owner_axis_bindings.items())},
        }
        return digest_payload(payload)

    @classmethod
    def load_jsonl(cls, paths: Iterable[str | Path]) -> "LawCatalog":
        from .runtime import passport_from_persisted
        catalog = cls()
        for path in paths:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    catalog.add_passport(passport_from_persisted(json.loads(line)))
        return catalog
