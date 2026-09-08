"""Continual-learning state for ScienceAtlas AI.

Three pieces the runtime lacked before this extension and cannot develop without:

``RegionalMetaLearner``
    Credit assignment conditioned on ``(owner_id, regime, domain)`` instead of a
    single scalar per owner, with explicit backoff when a region has no history.

``AlphaLedger``
    A lifetime budget of statistical tests.  Every genesis run and every
    promotion spends alpha; only genuinely new independent samples grant more.
    Without this, family-wise error over the lifetime of a self-expanding system
    is unbounded no matter how correct each individual null is.

    The search itself is charged in ``OperatorGenesisOwner.run`` via
    ``genesis_shells.SearchPricing``, before the search happens and regardless of
    its outcome.  An earlier revision charged only on promotion, which left
    rejected runs free and untraced: the cheapest possible retry-until-lucky
    loop.  Rejected runs are now the ones that matter most, because they are
    what a search does most of the time.

``GenesisState``
    Certificates, quarantine and revocation, plus rehydration of synthesised
    owners after a state restore.  Rehydration is the reason a synthesised
    operator survives a restart: the family is data, so the owner is rebuilt
    from its certificate and attached to the bus over the ``DetachedOwner`` that
    ``ScienceAtlasAI.from_json`` installed for it.

Note on revocation: ``OwnerBus`` has no unregister, and that is correct.
``owner_specs`` is part of ``authoritative_components()`` and therefore of the
snapshot root, so deleting an owner would rewrite history.  Revocation is a
status change plus exclusion from routing, never a deletion.

No Atlas coupling: nothing here imports ``atlas_bridge`` or touches
``atlas_registry_snapshot``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .genesis_shells import GenesisJournal
from .operator_genesis import GenesisBudget, OperatorCertificate, SynthesizedMechanismOwner


def _new_journal() -> GenesisJournal:
    return GenesisJournal()
from .owners import DetachedOwner, OwnerBus
from .provenance import digest_json
from .types import ValidationOutcome


NEUTRAL_PRIOR_BP = 5_000
PRIOR_WEIGHT = 4
"""Pseudo-observations of the neutral prior.  Small, so a region moves after a
handful of real outcomes, but non-zero, so one lucky outcome does not pin a
strategy score at an extreme."""


# ---------------------------------------------------------------------------
# Regional credit assignment
# ---------------------------------------------------------------------------


def region_key(owner_id: str, regime: str, domain: str) -> str:
    return f"{owner_id}|{regime}|{domain}"


@dataclass
class RegionalMetaLearner:
    """Strategy scores per ``(owner_id, regime, domain)``.

    Integer arithmetic throughout: ``canonical_bytes`` rejects floats from
    authoritative digest material, so posteriors are stored as counts and
    summed basis points, never as ratios.
    """

    trials: dict[str, int] = field(default_factory=dict)
    successes: dict[str, int] = field(default_factory=dict)
    gain_bp_total: dict[str, int] = field(default_factory=dict)
    validated_families: dict[str, list[str]] = field(default_factory=dict)

    @staticmethod
    def _effective_bp(outcome: ValidationOutcome) -> int:
        """A failed prediction contributes evidence, not credit."""
        return int(outcome.prediction_gain_bp) if outcome.success else 0

    def update(self, outcome: ValidationOutcome, *, regime: str, domain: str, family: str | None = None) -> int:
        if outcome.owner_id == "multi-owner":
            raise ValueError("regional credit must be attributed to a concrete owner")
        for key in self._keys(outcome.owner_id, regime, domain):
            self.trials[key] = self.trials.get(key, 0) + 1
            self.successes[key] = self.successes.get(key, 0) + (1 if outcome.success else 0)
            self.gain_bp_total[key] = self.gain_bp_total.get(key, 0) + self._effective_bp(outcome)
        if outcome.success and family:
            exact = region_key(outcome.owner_id, regime, domain)
            bucket = self.validated_families.setdefault(exact, [])
            if family not in bucket:
                bucket.append(family)
                bucket.sort()
        return self.score_bp(outcome.owner_id, regime=regime, domain=domain)[0]

    @staticmethod
    def _keys(owner_id: str, regime: str, domain: str) -> tuple[str, ...]:
        """Exact region plus the coarser levels used for backoff."""
        return (
            region_key(owner_id, regime, domain),
            region_key(owner_id, regime, "*"),
            region_key(owner_id, "*", domain),
            region_key(owner_id, "*", "*"),
        )

    def score_bp(self, owner_id: str, *, regime: str, domain: str) -> tuple[int, str]:
        """Shrunk score and the backoff level that produced it.

        Returns the most specific level with at least one trial, so a strategy
        that works in one regime is not credited in a regime it never ran in.
        """
        for level, key in zip(("exact", "regime", "domain", "owner"), self._keys(owner_id, regime, domain)):
            n = self.trials.get(key, 0)
            if n <= 0:
                continue
            total = PRIOR_WEIGHT * NEUTRAL_PRIOR_BP + self.gain_bp_total.get(key, 0)
            return (total // (PRIOR_WEIGHT + n), level)
        return (NEUTRAL_PRIOR_BP, "prior")

    def rank_owners(self, owner_ids: Sequence[str], *, regime: str, domain: str) -> tuple[str, ...]:
        scored = [
            (-self.score_bp(oid, regime=regime, domain=domain)[0], oid)
            for oid in owner_ids
        ]
        return tuple(oid for _, oid in sorted(scored))

    def seed_owner(self, owner_id: str, *, regime: str, domain: str, prior_bp: int, weight: int = PRIOR_WEIGHT) -> None:
        """Enter a new owner below the neutral prior without inventing outcomes.

        Recorded as synthetic trials so the shrinkage estimator treats it as a
        prior, not as evidence: it decays as soon as real outcomes arrive.
        """
        if not 0 <= prior_bp <= 10_000 or weight < 1:
            raise ValueError("invalid seed prior")
        key = region_key(owner_id, regime, domain)
        self.trials[key] = self.trials.get(key, 0) + weight
        self.gain_bp_total[key] = self.gain_bp_total.get(key, 0) + prior_bp * weight

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-regional-meta-v1",
            "prior_weight": PRIOR_WEIGHT,
            "trials": {k: self.trials[k] for k in sorted(self.trials)},
            "successes": {k: self.successes[k] for k in sorted(self.successes)},
            "gain_bp_total": {k: self.gain_bp_total[k] for k in sorted(self.gain_bp_total)},
            "validated_families": {k: list(self.validated_families[k]) for k in sorted(self.validated_families)},
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "RegionalMetaLearner":
        return cls(
            trials={str(k): int(v) for k, v in payload.get("trials", {}).items()},
            successes={str(k): int(v) for k, v in payload.get("successes", {}).items()},
            gain_bp_total={str(k): int(v) for k, v in payload.get("gain_bp_total", {}).items()},
            validated_families={str(k): [str(x) for x in v] for k, v in payload.get("validated_families", {}).items()},
        )


# ---------------------------------------------------------------------------
# Lifetime alpha budget
# ---------------------------------------------------------------------------


@dataclass
class AlphaLedger:
    """Persistent evidence-scoped lifetime alpha ledger.

    Alpha is created once per *evidence fingerprint*, not once per caller-chosen
    sample label. ``sample_id`` is only an alias used by the world model.  The
    persistent fingerprint is supplied by the acquisition boundary and remains
    bound to the scientific support of that evidence: ``(domain, axes)``.

    A search can spend only credits whose support covers every axis used by the
    search. Spending consumes the underlying evidence credit globally, so one
    observation cannot subsidise several unrelated contexts. There is deliberately
    no fixed balance ceiling; reachable shell depth is limited by compatible
    independent evidence and preregistered search price.

    The ledger cannot prove statistical independence from bytes alone. It therefore
    requires a stable upstream evidence identity for scoped scientific credit and
    fails closed when that fingerprint is absent. Wildcard/no-fingerprint grants are
    retained only as legacy bookkeeping and cannot finance scoped scientific search.
    """

    granted_bp: int = 0
    spent_bp: int = 0
    samples_credited: int = 0
    bp_per_sample: int = 25
    max_balance_bp: None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    credited_sample_ids: list[str] = field(default_factory=list)
    credited_evidence_fingerprints: list[str] = field(default_factory=list)
    sample_evidence_fingerprint: dict[str, str] = field(default_factory=dict)
    evidence_credits: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def balance_bp(self) -> int:
        return sum(max(0, int(c.get("remaining_bp", 0))) for c in self.evidence_credits.values())

    @staticmethod
    def _norm_axes(axes: Sequence[str] | None) -> tuple[str, ...]:
        if axes is None:
            return ("*",)
        out = tuple(sorted({str(a) for a in axes if str(a)}))
        return out or ("*",)

    @staticmethod
    def _is_scoped(domain: str, axes: tuple[str, ...]) -> bool:
        return str(domain) != "*" or axes != ("*",)

    @staticmethod
    def _compatible(credit: Mapping[str, Any], *, domain: str, axes: tuple[str, ...]) -> bool:
        # A legacy sample-label credit is migration bookkeeping only.  It may be
        # consumed by an equally legacy wildcard query, never by a scoped search.
        identity_mode = str(credit.get("identity_mode", "EVIDENCE_FINGERPRINT"))
        if identity_mode != "EVIDENCE_FINGERPRINT" and AlphaLedger._is_scoped(domain, axes):
            return False
        cdom = str(credit.get("domain", "*"))
        caxes = set(str(a) for a in credit.get("axes", ["*"]))
        domain_ok = cdom == "*" or domain == "*" or cdom == domain
        axes_ok = "*" in caxes or axes == ("*",) or set(axes).issubset(caxes)
        return domain_ok and axes_ok

    @staticmethod
    def _same_or_narrower_support(credit: Mapping[str, Any], *, domain: str, axes: tuple[str, ...]) -> bool:
        """Whether an alias claim does not widen the support of existing evidence."""
        cdom = str(credit.get("domain", "*"))
        caxes = set(str(a) for a in credit.get("axes", ["*"]))
        domain_ok = cdom == "*" or cdom == str(domain)
        axes_ok = "*" in caxes or set(axes).issubset(caxes)
        return domain_ok and axes_ok

    @staticmethod
    def _legacy_fingerprint(sample_id: str) -> str:
        return digest_json(
            {"legacy_sample_id": str(sample_id)},
            namespace=b"SCIENCEATLAS_AI_LEGACY_SAMPLE_IDENTITY_V1",
        )

    def grant_for_samples(
        self,
        new_sample_ids: Sequence[str],
        *,
        domain: str = "*",
        axes: Sequence[str] | None = None,
        evidence_fingerprints: Mapping[str, str] | None = None,
    ) -> int:
        """Credit each evidence identity at most once across aliases and restarts.

        For a scoped scientific grant, every ``sample_id`` must map to a non-empty
        stable evidence fingerprint. Re-labelling the same evidence with a new
        sample ID therefore creates no new alpha. A reused sample ID pointing to a
        different fingerprint is an identity conflict and is refused.

        The unscoped ``domain='*', axes=None`` compatibility path can still import
        legacy sample-label credit, but that credit is marked ``LEGACY_SAMPLE_ID``
        and is ineligible for later scoped scientific spending.
        """
        support_axes = self._norm_axes(axes)
        scoped = self._is_scoped(str(domain), support_axes)
        supplied = {str(k): str(v).strip() for k, v in (evidence_fingerprints or {}).items()}
        known_samples = set(self.credited_sample_ids)
        known_fingerprints = set(self.credited_evidence_fingerprints)

        accepted: list[tuple[str, str, str]] = []  # (sample, fingerprint, identity_mode)
        duplicate_samples = 0
        duplicate_evidence_aliases = 0
        missing_fingerprints = 0
        identity_conflicts = 0
        support_conflicts = 0

        for raw in new_sample_ids:
            sample_id = str(raw)
            fingerprint = supplied.get(sample_id, "")
            identity_mode = "EVIDENCE_FINGERPRINT"
            if not fingerprint:
                if scoped:
                    missing_fingerprints += 1
                    continue
                fingerprint = self._legacy_fingerprint(sample_id)
                identity_mode = "LEGACY_SAMPLE_ID"

            previous = self.sample_evidence_fingerprint.get(sample_id)
            if previous is not None:
                if previous == fingerprint:
                    duplicate_samples += 1
                else:
                    identity_conflicts += 1
                continue

            existing = self.evidence_credits.get(fingerprint)
            if existing is not None:
                if not self._same_or_narrower_support(existing, domain=str(domain), axes=support_axes):
                    support_conflicts += 1
                    continue
                # New sample alias for the same evidence: record the alias but mint
                # no alpha. This is the cross-alias dedup invariant.
                self.sample_evidence_fingerprint[sample_id] = fingerprint
                known_samples.add(sample_id)
                aliases = set(str(x) for x in existing.get("sample_ids", []))
                aliases.add(sample_id)
                existing["sample_ids"] = sorted(aliases)
                duplicate_evidence_aliases += 1
                continue

            accepted.append((sample_id, fingerprint, identity_mode))
            self.sample_evidence_fingerprint[sample_id] = fingerprint
            known_samples.add(sample_id)
            known_fingerprints.add(fingerprint)
            self.evidence_credits[fingerprint] = {
                "evidence_fingerprint": fingerprint,
                "identity_mode": identity_mode,
                "sample_ids": [sample_id],
                "domain": str(domain),
                "axes": list(support_axes),
                "granted_bp": int(self.bp_per_sample),
                "remaining_bp": int(self.bp_per_sample),
            }

        self.credited_sample_ids = sorted(known_samples)
        self.credited_evidence_fingerprints = sorted(known_fingerprints)
        count = len(accepted)
        if count:
            delta = count * self.bp_per_sample
            self.granted_bp += delta
            self.samples_credited += count
            self.entries.append({
                "kind": "grant", "samples": count, "bp": delta,
                "domain": str(domain), "axes": list(support_axes),
                "sample_ids": sorted(sample_id for sample_id, _, _ in accepted),
                "evidence_fingerprints": sorted(fp for _, fp, _ in accepted),
                "duplicate_samples_refused": duplicate_samples,
                "duplicate_evidence_aliases_refused": duplicate_evidence_aliases,
                "missing_evidence_fingerprints_refused": missing_fingerprints,
                "identity_conflicts_refused": identity_conflicts,
                "support_conflicts_refused": support_conflicts,
            })
        elif any((duplicate_samples, duplicate_evidence_aliases, missing_fingerprints, identity_conflicts, support_conflicts)):
            self.entries.append({
                "kind": "grant_refused", "samples": 0, "bp": 0,
                "domain": str(domain), "axes": list(support_axes),
                "duplicate_samples_refused": duplicate_samples,
                "duplicate_evidence_aliases_refused": duplicate_evidence_aliases,
                "missing_evidence_fingerprints_refused": missing_fingerprints,
                "identity_conflicts_refused": identity_conflicts,
                "support_conflicts_refused": support_conflicts,
            })
        return self.balance_bp

    def compatible_balance_bp(self, *, domain: str = "*", axes: Sequence[str] | None = None) -> int:
        qaxes = self._norm_axes(axes)
        return sum(
            max(0, int(c.get("remaining_bp", 0)))
            for c in self.evidence_credits.values()
            if self._compatible(c, domain=str(domain), axes=qaxes)
        )

    def can_spend(
        self,
        alpha_bp: int,
        *,
        domain: str = "*",
        axes: Sequence[str] | None = None,
    ) -> bool:
        return alpha_bp > 0 and self.compatible_balance_bp(domain=domain, axes=axes) >= alpha_bp

    def spend(
        self,
        alpha_bp: int,
        *,
        purpose: str,
        domain: str = "*",
        axes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        requested = int(alpha_bp)
        qaxes = self._norm_axes(axes)
        compatible = self.compatible_balance_bp(domain=domain, axes=qaxes)
        if requested <= 0 or compatible < requested:
            receipt = {
                "schema": "scienceatlas-ai-alpha-spend-v2",
                "status": "REFUSED_INSUFFICIENT_COMPATIBLE_ALPHA",
                "requested_bp": requested,
                "compatible_balance_bp": compatible,
                "balance_bp": self.balance_bp,
                "domain": str(domain), "axes": list(qaxes), "purpose": purpose,
            }
            receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ALPHA_SPEND_V2")
            return receipt
        remaining = requested
        consumed: list[dict[str, Any]] = []
        for fingerprint in sorted(self.evidence_credits):
            credit = self.evidence_credits[fingerprint]
            if not self._compatible(credit, domain=str(domain), axes=qaxes):
                continue
            available = max(0, int(credit.get("remaining_bp", 0)))
            if not available:
                continue
            take = min(available, remaining)
            credit["remaining_bp"] = available - take
            consumed.append({"evidence_fingerprint": fingerprint, "bp": take})
            remaining -= take
            if remaining == 0:
                break
        if remaining:
            raise RuntimeError("alpha ledger compatibility accounting invariant violated")
        self.spent_bp += requested
        self.entries.append({
            "kind": "spend", "bp": requested, "purpose": purpose,
            "domain": str(domain), "axes": list(qaxes), "credits": consumed,
        })
        receipt = {
            "schema": "scienceatlas-ai-alpha-spend-v2",
            "status": "SPENT",
            "requested_bp": requested,
            "compatible_balance_bp": self.compatible_balance_bp(domain=domain, axes=qaxes),
            "balance_bp": self.balance_bp,
            "domain": str(domain), "axes": list(qaxes), "purpose": purpose,
            "credits": consumed,
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ALPHA_SPEND_V2")
        return receipt

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-alpha-ledger-v2",
            "granted_bp": self.granted_bp,
            "spent_bp": self.spent_bp,
            "balance_bp": self.balance_bp,
            "samples_credited": self.samples_credited,
            "bp_per_sample": self.bp_per_sample,
            "max_balance_bp": None,
            "credited_sample_ids": list(self.credited_sample_ids),
            "credited_evidence_fingerprints": list(self.credited_evidence_fingerprints),
            "sample_evidence_fingerprint": {k: self.sample_evidence_fingerprint[k] for k in sorted(self.sample_evidence_fingerprint)},
            "evidence_credits": {k: dict(self.evidence_credits[k]) for k in sorted(self.evidence_credits)},
            "entries": [dict(e) for e in self.entries],
            "claim_boundary": {
                "is_calibrated_familywise_procedure": False,
                "meaning": "bookkeeping of tests spent against independent evidence with persistent evidence identity and domain/axis support",
                "fixed_balance_ceiling": None,
                "cross_context_double_spend_allowed": False,
                "sample_alias_can_mint_new_alpha": False,
                "upstream_stable_evidence_identity_required": True,
            },
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "AlphaLedger":
        schema = str(payload.get("schema", ""))
        if schema.endswith("v2") and "credited_evidence_fingerprints" in payload:
            return cls(
                granted_bp=int(payload.get("granted_bp", 0)),
                spent_bp=int(payload.get("spent_bp", 0)),
                samples_credited=int(payload.get("samples_credited", 0)),
                bp_per_sample=int(payload.get("bp_per_sample", 25)),
                entries=[dict(e) for e in payload.get("entries", [])],
                credited_sample_ids=[str(x) for x in payload.get("credited_sample_ids", [])],
                credited_evidence_fingerprints=[str(x) for x in payload.get("credited_evidence_fingerprints", [])],
                sample_evidence_fingerprint={str(k): str(v) for k, v in payload.get("sample_evidence_fingerprint", {}).items()},
                evidence_credits={str(k): dict(v) for k, v in payload.get("evidence_credits", {}).items()},
            )

        # Migration from the earlier sample-ID ledger (v1 and pre-seal v2): the
        # numerical credit is preserved for audit, but its identity mode is legacy
        # and therefore cannot finance a scoped scientific search after migration.
        obj = cls(
            granted_bp=int(payload.get("granted_bp", 0)),
            spent_bp=int(payload.get("spent_bp", 0)),
            samples_credited=int(payload.get("samples_credited", 0)),
            bp_per_sample=int(payload.get("bp_per_sample", 25)),
            entries=[dict(e) for e in payload.get("entries", [])],
        )
        prior_credits = payload.get("evidence_credits", {})
        if prior_credits:
            for sample_id, raw_credit in prior_credits.items():
                sid = str(sample_id)
                fp = cls._legacy_fingerprint(sid)
                credit = dict(raw_credit)
                credit.update({
                    "evidence_fingerprint": fp,
                    "identity_mode": "LEGACY_SAMPLE_ID",
                    "sample_ids": [sid],
                })
                obj.evidence_credits[fp] = credit
                obj.sample_evidence_fingerprint[sid] = fp
                obj.credited_sample_ids.append(sid)
                obj.credited_evidence_fingerprints.append(fp)
        else:
            granted = int(payload.get("granted_bp", 0))
            spent = int(payload.get("spent_bp", 0))
            balance = max(0, granted - spent)
            if balance:
                sid = "legacy-v1-balance"
                fp = cls._legacy_fingerprint(sid)
                obj.credited_sample_ids = [sid]
                obj.credited_evidence_fingerprints = [fp]
                obj.sample_evidence_fingerprint[sid] = fp
                obj.evidence_credits[fp] = {
                    "evidence_fingerprint": fp,
                    "identity_mode": "LEGACY_SAMPLE_ID",
                    "sample_ids": [sid],
                    "domain": "*", "axes": ["*"],
                    "granted_bp": balance, "remaining_bp": balance,
                }
        obj.credited_sample_ids = sorted(set(obj.credited_sample_ids))
        obj.credited_evidence_fingerprints = sorted(set(obj.credited_evidence_fingerprints))
        return obj


# ---------------------------------------------------------------------------
# Genesis state: certificates, quarantine, revocation, rehydration
# ---------------------------------------------------------------------------


@dataclass
class GenesisState:
    certificates: dict[str, OperatorCertificate] = field(default_factory=dict)
    owner_certificate: dict[str, str] = field(default_factory=dict)
    quarantine: dict[str, int] = field(default_factory=dict)
    consecutive_failures: dict[str, int] = field(default_factory=dict)
    revoked_owner_ids: list[str] = field(default_factory=list)
    ledger: AlphaLedger = field(default_factory=AlphaLedger)
    journal: "GenesisJournal" = field(default_factory=lambda: _new_journal())
    revocation_failure_threshold: int = 3

    # -- promotion ---------------------------------------------------------

    def promote(
        self,
        certificate: OperatorCertificate,
        *,
        budget: GenesisBudget,
        bus: OwnerBus,
        meta: RegionalMetaLearner | None = None,
        regime: str = "*",
        domain: str = "*",
    ) -> tuple[SynthesizedMechanismOwner | None, dict[str, Any]]:
        """Register a certified operator, paying alpha and entering quarantine."""
        if certificate.status != "PROMOTED":
            return (None, {"status": "REFUSED_NOT_PROMOTED"})
        if not certificate.alpha_receipt_digest:
            return (None, {"status": "REFUSED_UNPRICED_CERTIFICATE"})
        # Promotion is charged on top of the search, against the same scientific
        # evidence support. An unrelated domain cannot subsidise this promotion.
        receipt = self.ledger.spend(
            budget.alpha_bp, purpose=f"promote:{certificate.digest[:12]}",
            domain=certificate.search_domain,
            axes=tuple(certificate.family.input_axes) + (certificate.target_axis,),
        )
        if receipt["status"] != "SPENT":
            return (None, {"status": "REFUSED_ALPHA_EXHAUSTED", "alpha_receipt": receipt})
        owner = SynthesizedMechanismOwner(certificate=certificate)
        bus.register(owner)
        self.certificates[certificate.digest] = certificate
        self.owner_certificate[owner.spec.owner_id] = certificate.digest
        self.quarantine[owner.spec.owner_id] = budget.quarantine_epochs
        if meta is not None:
            meta.seed_owner(owner.spec.owner_id, regime=regime, domain=domain, prior_bp=budget.promoted_prior_bp)
        return (owner, {"status": "PROMOTED", "owner_id": owner.spec.owner_id, "alpha_receipt": receipt})

    # -- quarantine --------------------------------------------------------

    def credit_allowed(self, owner_id: str) -> bool:
        return self.quarantine.get(owner_id, 0) <= 0

    def tick_epoch(self) -> None:
        for owner_id in sorted(self.quarantine):
            if self.quarantine[owner_id] > 0:
                self.quarantine[owner_id] -= 1

    # -- revocation --------------------------------------------------------

    def observe_outcome(self, outcome: ValidationOutcome) -> dict[str, Any] | None:
        """Route a validation outcome to the falsification contract.

        Only synthesised owners are subject to revocation; built-in owners have
        their own falsification contracts and are not certificate-backed.
        """
        owner_id = outcome.owner_id
        if owner_id not in self.owner_certificate:
            return None
        if owner_id in self.revoked_owner_ids:
            return {"status": "ALREADY_REVOKED", "owner_id": owner_id}
        if outcome.success:
            self.consecutive_failures[owner_id] = 0
            return {"status": "CONFIRMED", "owner_id": owner_id}
        count = self.consecutive_failures.get(owner_id, 0) + 1
        self.consecutive_failures[owner_id] = count
        if count < self.revocation_failure_threshold:
            return {"status": "FAILURE_RECORDED", "owner_id": owner_id, "consecutive_failures": count}
        return self.revoke(owner_id, reason=f"{count} consecutive prospective failures")

    def revoke(self, owner_id: str, *, reason: str) -> dict[str, Any]:
        digest = self.owner_certificate[owner_id]
        revoked = self.certificates[digest].revoked(reason)
        self.certificates[digest] = revoked
        if owner_id not in self.revoked_owner_ids:
            self.revoked_owner_ids.append(owner_id)
            self.revoked_owner_ids.sort()
        self.quarantine.pop(owner_id, None)
        return {
            "status": "REVOKED",
            "owner_id": owner_id,
            "certificate_digest": digest,
            "revoked_digest": revoked.digest,
            "reason": reason,
        }

    def active_owner_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.owner_certificate) - set(self.revoked_owner_ids)))

    def active_capabilities(self, bus: OwnerBus) -> tuple[str, ...]:
        out = []
        for owner_id in self.active_owner_ids():
            owner = bus.get(owner_id)
            if not isinstance(owner, DetachedOwner):
                out.append(owner.spec.capability)
        return tuple(sorted(out))

    # -- rehydration -------------------------------------------------------

    def rehydrate(self, bus: OwnerBus) -> dict[str, Any]:
        """Rebuild live synthesised owners over their restored detached specs.

        ``ScienceAtlasAI.from_json`` registers every non-built-in owner as a
        ``DetachedOwner``.  A synthesised owner is fully determined by its
        certificate, so it is reconstructed here rather than mounted from an
        external distribution, and attached through the existing narrow
        ``OwnerBus.attach`` path (identical spec required).
        """
        attached: list[str] = []
        skipped: list[dict[str, str]] = []
        for owner_id in sorted(self.owner_certificate):
            digest = self.owner_certificate[owner_id]
            certificate = self.certificates.get(digest)
            if certificate is None:
                skipped.append({"owner_id": owner_id, "reason": "certificate missing"})
                continue
            if certificate.status != "PROMOTED":
                skipped.append({"owner_id": owner_id, "reason": f"certificate {certificate.status.lower()}"})
                continue
            owner = SynthesizedMechanismOwner(certificate=certificate)
            if owner.spec.owner_id != owner_id:
                skipped.append({"owner_id": owner_id, "reason": "rebuilt owner identity mismatch"})
                continue
            try:
                bus.attach(owner)
            except (KeyError, ValueError) as exc:
                skipped.append({"owner_id": owner_id, "reason": str(exc)})
                continue
            attached.append(owner_id)
        payload = {
            "schema": "scienceatlas-ai-genesis-rehydration-v1",
            "attached": attached,
            "skipped": skipped,
            "revoked": list(self.revoked_owner_ids),
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_GENESIS_REHYDRATION_V1")
        return payload

    # -- serialisation -----------------------------------------------------

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-genesis-state-v1",
            "certificates": {k: self.certificates[k].to_json() for k in sorted(self.certificates)},
            "owner_certificate": {k: self.owner_certificate[k] for k in sorted(self.owner_certificate)},
            "quarantine": {k: self.quarantine[k] for k in sorted(self.quarantine)},
            "consecutive_failures": {k: self.consecutive_failures[k] for k in sorted(self.consecutive_failures)},
            "revoked_owner_ids": list(self.revoked_owner_ids),
            "ledger": self.ledger.to_json(),
            "journal": self.journal.to_json(),
            "revocation_failure_threshold": self.revocation_failure_threshold,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "GenesisState":
        from .operator_genesis import FamilySpec

        certificates: dict[str, OperatorCertificate] = {}
        for key, row in payload.get("certificates", {}).items():
            certificates[str(key)] = OperatorCertificate(
                family=FamilySpec.from_json(row["family"]),
                target_axis=str(row["target_axis"]),
                status=str(row["status"]),
                gates=tuple((str(a), str(b)) for a, b in row.get("gates", [])),
                sealed_gain_bp=int(row.get("sealed_gain_bp", 0)),
                families_examined=int(row.get("families_examined", 0)),
                budget_digest=str(row.get("budget_digest", "")),
                split_digest=str(row.get("split_digest", "")),
                null_receipt_digest=str(row.get("null_receipt_digest", "")),
                incumbent_owner_ids=tuple(str(x) for x in row.get("incumbent_owner_ids", [])),
                quarantine_epochs_remaining=int(row.get("quarantine_epochs_remaining", 0)),
                revocation_reason=str(row.get("revocation_reason", "")),
                shell_index=int(row.get("shell_index", 0)),
                shell_id=str(row.get("shell_id", "")),
                alpha_price_bp=int(row.get("alpha_price_bp", 0)),
                run_id=str(row.get("run_id", "")),
                search_domain=str(row.get("search_domain", "*")),
                alpha_receipt_digest=str(row.get("alpha_receipt_digest", "")),
            )
        return cls(
            certificates=certificates,
            owner_certificate={str(k): str(v) for k, v in payload.get("owner_certificate", {}).items()},
            quarantine={str(k): int(v) for k, v in payload.get("quarantine", {}).items()},
            consecutive_failures={str(k): int(v) for k, v in payload.get("consecutive_failures", {}).items()},
            revoked_owner_ids=[str(x) for x in payload.get("revoked_owner_ids", [])],
            ledger=AlphaLedger.from_json(payload.get("ledger", {})),
            journal=GenesisJournal.from_json(payload.get("journal", {})),
            revocation_failure_threshold=int(payload.get("revocation_failure_threshold", 3)),
        )


__all__ = [
    "AlphaLedger",
    "GenesisState",
    "NEUTRAL_PRIOR_BP",
    "PRIOR_WEIGHT",
    "RegionalMetaLearner",
    "region_key",
]
