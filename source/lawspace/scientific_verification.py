"""Domain-neutral scientific verification core for Φ-LawSpace v8.0.

This module is the single authoritative owner of generic scientific evidence
rules. Domain owners may implement domain semantics, equations and compatibility
constraints, but they must not reimplement source authenticity, source-lock,
semantic-null, contradiction, entity identity, evidence-class or generic claim
boundary logic.

Trust model
-----------
Raw evidence is untrusted. A plausible PMID/DOI/URL/accession/title is not
scientific evidence. World evidence requires a chain:

  EvidenceProposal
    -> SourceResolution (actual external resolution or trusted ingestion)
    -> SourceVerificationReceipt (cryptographically attested)
    -> ClaimVerificationReceipt (independent reviewer + source-content binding)
    -> ScientificVerificationCore.verify_bundle()

A SHA-256 digest only provides integrity. World authorization additionally
requires Ed25519 attestations whose private keys are not shipped in the release.
Qualification keys are deliberately public/test-only and can never enable world
promotion. Serialized ScientificVerificationReceipt objects are audit artifacts,
not authorization tokens; downstream owners must recompute from the bundle.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .schema import digest_payload

OWNER_ID = "SCIENTIFIC-VERIFICATION-CORE/8.0.0"
SOURCE_RESOLVER_OWNER_ID = "EXTERNAL-SOURCE-RESOLUTION/8.0.0"
SOURCE_VERIFIER_OWNER_ID = "INDEPENDENT-SOURCE-VERIFIER/8.0.0"
CLAIM_VERIFIER_OWNER_ID = "INDEPENDENT-CLAIM-VERIFIER/8.0.0"
ARTIFACT_VERIFIER_OWNER_ID = "INDEPENDENT-ARTIFACT-VERIFIER/8.0.0"
SCHEMA = "phi-scientific-verification/v8.0"
SOURCE_RECEIPT_SCHEMA = "phi-source-verification-receipt/v8.0"
CLAIM_RECEIPT_SCHEMA = "phi-claim-verification-receipt/v8.0"
ARTIFACT_RECEIPT_SCHEMA = "phi-artifact-verification-receipt/v8.0"
VERIFICATION_RECEIPT_SCHEMA = "phi-scientific-verification-receipt/v8.0"
TRUST_STORE_SCHEMA = "phi-scientific-verifier-trust-store/v8.0"

TRUST_TIER_WORLD = "WORLD"
TRUST_TIER_QUALIFICATION = "QUALIFICATION"
QUALIFICATION_SOURCE_KEY_ID = "phi-v8-qualification-source-ed25519"
QUALIFICATION_CLAIM_KEY_ID = "phi-v8-qualification-claim-ed25519"
QUALIFICATION_ARTIFACT_KEY_ID = "phi-v8-qualification-artifact-ed25519"
# Deliberately non-secret deterministic test keys. Receipts signed with these are
# QUALIFICATION-only and are structurally prohibited from world claims. Separate
# keys exercise the same role-separation invariant required from WORLD services.
_QUALIFICATION_SOURCE_PRIVATE_SEED = bytes.fromhex(
    "8f6db6502e3340cb36d60398a25ec6c204ef1170f1d48ad9993a86a4cc201a71"
)
_QUALIFICATION_CLAIM_PRIVATE_SEED = bytes.fromhex(
    "1f7d9e42b685b2ef36f2f9e97f8234a667f0d7e7ac91a1a17d14ff19c1664c22"
)
_QUALIFICATION_ARTIFACT_PRIVATE_SEED = bytes.fromhex(
    "c34ee275c4cd4b6b25d93060aeb0743d93d7b638483faf998617bcbcc0fa3e18"
)

SEMANTIC_NULL_EXACT = {
    "UNKNOWN", "UNMEASURED", "NOT_MEASURED", "NOT_RUN", "NOT_DEFINED",
    "UNFIT", "TO_BE_DEFINED", "TBD", "NA", "N/A", "NONE", "NULL",
    "UNSPECIFIED", "NOT_ESTABLISHED", "INSUFFICIENT",
}
SEMANTIC_NULL_PREFIXES = (
    "UNKNOWN_", "UNMEASURED_", "NOT_MEASURED_", "NOT_RUN_", "NOT_DEFINED_",
    "UNFIT_", "TO_BE_DEFINED_", "NOT_ESTABLISHED_", "NO_HUMAN_TRIAL",
    "UNKNOWN_NO_", "NOT_APPLICABLE_NO_", "UNSPECIFIED_CANDIDATE_",
)
SOURCE_IDENTIFIER_TYPES = {
    "PMID", "DOI", "URL", "ARXIV", "UNIPROT", "HGNC", "NCBI_GENE",
    "CLINICALTRIALS", "ACCESSION", "CATALOG_ID", "OTHER",
}
TRUSTED_RESOLUTION_METHODS = {
    "LIVE_EXTERNAL_RESOLUTION", "TRUSTED_DATABASE_RESOLUTION",
    "LOCAL_CONTENT_ADDRESSABLE_SNAPSHOT", "SCIENTIFIC_DATA_INGESTION",
    "QUALIFICATION_FIXTURE",
}
TRUSTED_REVIEW_METHODS = {
    "INDEPENDENT_MANUAL_REVIEW", "INDEPENDENT_MODEL_REVIEW",
    "STRUCTURED_DATABASE_ASSERTION", "EXACT_QUOTE_MATCH", "QUALIFICATION_FIXTURE",
}
CLAIM_RELATIONS = {"SUPPORTS", "CONTRADICTS", "QUALIFIES", "IDENTIFIES"}
ENTITY_RESOLUTION_STATES = {
    "ESTABLISHED_EXTERNAL", "DEFINED_INTERNAL", "SYNTHETIC_CONTROL", "UNRESOLVED"
}
DEFAULT_TRUSTED_RESOLVER_OWNERS = {
    SOURCE_RESOLVER_OWNER_ID, "EXTERNAL-WEB-RESOLVER", "SCIENTIFIC-DATA-INGESTION",
    "TRUSTED-DATABASE-RESOLVER", "SCIENTIFIC-VERIFICATION-QUALIFICATION",
}
DEFAULT_TRUSTED_REVIEWER_OWNERS = {
    CLAIM_VERIFIER_OWNER_ID, "INDEPENDENT-SCIENTIFIC-REVIEWER",
    "SCIENTIFIC-VERIFICATION-QUALIFICATION-REVIEWER",
}
DEFAULT_TRUSTED_ARTIFACT_VERIFIER_OWNERS = {
    ARTIFACT_VERIFIER_OWNER_ID, "SCIENTIFIC-VERIFICATION-QUALIFICATION-ARTIFACT",
}



def content_addressed_digest(content: Any) -> str:
    """Canonical digest used to bind internal evidence artifacts to runtime payloads."""
    return hashlib.sha256(digest_payload(content).encode("ascii")).hexdigest()

def semantic_state(value: Any) -> str:
    if value in (None, "", (), [], {}):
        return "MISSING"
    if isinstance(value, str):
        token = re.sub(r"\s+", "_", value.strip().upper())
        if token in SEMANTIC_NULL_EXACT or any(token.startswith(p) for p in SEMANTIC_NULL_PREFIXES):
            return "SEMANTIC_NULL"
    return "USABLE"


def is_usable(value: Any) -> bool:
    return semantic_state(value) == "USABLE"


def normalize_status(value: Any, default: str = "INSUFFICIENT") -> str:
    return str(value if value not in (None, "") else default).strip().upper()


def gate(status: str, reason: str, **extra: Any) -> Mapping[str, Any]:
    return {"status": status, "reason": reason, **extra}


def _sha256_hex(value: Any) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "").strip().lower()))


def _normalise_identifier(kind: str, value: Any) -> str:
    text = str(value or "").strip()
    kind = kind.upper()
    if kind == "DOI":
        return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.I).lower()
    if kind == "PMID":
        return re.sub(r"^PMID\s*:?\s*", "", text, flags=re.I)
    if kind == "ARXIV":
        return re.sub(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:)", "", text, flags=re.I).removesuffix(".pdf")
    if kind == "URL":
        return text.rstrip("/")
    return text


def _qualification_private_key(role: str) -> Ed25519PrivateKey:
    role = str(role).upper()
    seed = {
        "SOURCE": _QUALIFICATION_SOURCE_PRIVATE_SEED,
        "CLAIM": _QUALIFICATION_CLAIM_PRIVATE_SEED,
        "ARTIFACT": _QUALIFICATION_ARTIFACT_PRIVATE_SEED,
    }.get(role)
    if seed is None:
        raise ValueError(f"unsupported qualification role {role!r}")
    return Ed25519PrivateKey.from_private_bytes(seed)


def _public_key_b64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def _trust_store_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "trust" / "scientific_verifier_public_keys.json"


def load_trust_store(path: str | Path | None = None) -> Mapping[str, Any]:
    env_path = os.environ.get("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH", "").strip()
    store_path = Path(path) if path else (Path(env_path) if env_path else _trust_store_path())
    keys: dict[str, Any] = {
        QUALIFICATION_SOURCE_KEY_ID: {
            "public_key_b64": _public_key_b64(_qualification_private_key("SOURCE")),
            "trust_tier": TRUST_TIER_QUALIFICATION, "roles": ["SOURCE"],
            "authorized_owners": ["SCIENTIFIC-VERIFICATION-QUALIFICATION"],
            "purpose": "DETERMINISTIC_SOURCE_ENGINE_QUALIFICATION_ONLY",
            "private_key_shipped": True, "external_service_required": False,
        },
        QUALIFICATION_CLAIM_KEY_ID: {
            "public_key_b64": _public_key_b64(_qualification_private_key("CLAIM")),
            "trust_tier": TRUST_TIER_QUALIFICATION, "roles": ["CLAIM"],
            "authorized_owners": ["SCIENTIFIC-VERIFICATION-QUALIFICATION-REVIEWER"],
            "purpose": "DETERMINISTIC_CLAIM_ENGINE_QUALIFICATION_ONLY",
            "private_key_shipped": True, "external_service_required": False,
        },
        QUALIFICATION_ARTIFACT_KEY_ID: {
            "public_key_b64": _public_key_b64(_qualification_private_key("ARTIFACT")),
            "trust_tier": TRUST_TIER_QUALIFICATION, "roles": ["ARTIFACT"],
            "authorized_owners": ["SCIENTIFIC-VERIFICATION-QUALIFICATION-ARTIFACT"],
            "purpose": "DETERMINISTIC_ARTIFACT_ENGINE_QUALIFICATION_ONLY",
            "private_key_shipped": True, "external_service_required": False,
        },
    }
    if store_path.is_file():
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        if payload.get("schema") != TRUST_STORE_SCHEMA:
            raise ValueError("unsupported scientific verifier trust store schema")
        for key_id, row0 in dict(payload.get("keys", {})).items():
            row = dict(row0)
            tier = str(row.get("trust_tier", "")).upper()
            roles = {str(x).upper() for x in row.get("roles", ())}
            owners = {str(x) for x in row.get("authorized_owners", ())}
            # WORLD trust is deployment configuration, never a build convenience.
            # A WORLD key is ignored unless the release contains only its public key,
            # it is bound to exactly one verifier role, and an external signer owner
            # is declared. This prevents a generic/self-signing key from authorizing
            # arbitrary evidence.
            if tier == TRUST_TIER_WORLD:
                if row.get("private_key_shipped") is not False or len(roles) != 1 or not owners or row.get("external_service_required") is not True:
                    continue
            keys[str(key_id)] = row
    return {"schema": TRUST_STORE_SCHEMA, "keys": keys, "path": str(store_path)}


def _receipt_digest(payload: Mapping[str, Any], digest_key: str) -> Mapping[str, Any]:
    body = {k: v for k, v in dict(payload).items() if k not in {digest_key, "attestation_signature"}}
    return {**body, digest_key: digest_payload(body)}


def _receipt_digest_valid(receipt: Mapping[str, Any], digest_key: str) -> bool:
    expected = str(receipt.get(digest_key, ""))
    if not expected:
        return False
    body = {k: v for k, v in dict(receipt).items() if k not in {digest_key, "attestation_signature"}}
    return digest_payload(body) == expected


def _attest_receipt(
    receipt: Mapping[str, Any], *, digest_key: str, private_key: Ed25519PrivateKey, key_id: str,
    attestation_owner: str,
) -> Mapping[str, Any]:
    # Internal signer is used only by deterministic QUALIFICATION fixtures.
    # WORLD signing is intentionally not exposed by the runtime; external services
    # must sign the canonical receipt digest and return the completed receipt.
    body = dict(receipt)
    body["attestation_key_id"] = str(key_id)
    body["attestation_owner"] = str(attestation_owner)
    body.pop("attestation_signature", None)
    body = dict(_receipt_digest(body, digest_key))
    sig = private_key.sign(str(body[digest_key]).encode("ascii"))
    return {**body, "attestation_signature": base64.b64encode(sig).decode("ascii")}


def receipt_trust_tier(receipt: Mapping[str, Any], trust_store_path: str | Path | None = None) -> str:
    key_id = str(receipt.get("attestation_key_id", ""))
    store = load_trust_store(trust_store_path)
    return str(store.get("keys", {}).get(key_id, {}).get("trust_tier", "UNTRUSTED")).upper()


def _attestation_valid(
    receipt: Mapping[str, Any], *, digest_key: str, required_role: str,
    required_tier: str | None = None, trust_store_path: str | Path | None = None,
) -> bool:
    if not _receipt_digest_valid(receipt, digest_key):
        return False
    key_id = str(receipt.get("attestation_key_id", ""))
    sig_b64 = str(receipt.get("attestation_signature", ""))
    if not key_id or not sig_b64:
        return False
    row = dict(load_trust_store(trust_store_path).get("keys", {}).get(key_id, {}))
    if not row:
        return False
    if required_tier and str(row.get("trust_tier", "")).upper() != required_tier.upper():
        return False
    if required_role.upper() not in {str(x).upper() for x in row.get("roles", ())}:
        return False
    attestation_owner = str(receipt.get("attestation_owner", "")).strip()
    authorized_owners = {str(x) for x in row.get("authorized_owners", ())}
    if str(row.get("trust_tier", "")).upper() == TRUST_TIER_WORLD:
        if not attestation_owner or attestation_owner not in authorized_owners:
            return False
    elif authorized_owners and attestation_owner not in authorized_owners:
        return False
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(str(row["public_key_b64"]), validate=True))
        public.verify(base64.b64decode(sig_b64, validate=True), str(receipt[digest_key]).encode("ascii"))
        return True
    except (KeyError, ValueError, TypeError, InvalidSignature):
        return False


class ExternalSourceResolutionOwner:
    """Perform actual HTTPS resolution. This returns a resolution record, not evidence.

    A separate verifier process must still attest it. If network resolution is
    unavailable, the correct result is fail-closed rather than a guessed source.
    """
    owner_id = SOURCE_RESOLVER_OWNER_ID

    def resolve(
        self, *, identifier_type: str, identifier: str, expected_title: str = "",
        resolver_url: str = "", timeout_seconds: float = 30.0,
        maximum_size_bytes: int = 2_000_000,
    ) -> Mapping[str, Any]:
        kind = str(identifier_type).upper()
        declared = _normalise_identifier(kind, identifier)
        if kind == "PMID":
            url = f"https://pubmed.ncbi.nlm.nih.gov/{urllib.parse.quote(declared)}/?format=pubmed"
        elif kind == "DOI":
            url = f"https://doi.org/{urllib.parse.quote(declared, safe='/.:()_-')}"
        elif kind == "ARXIV":
            url = f"https://arxiv.org/abs/{urllib.parse.quote(declared)}"
        elif kind == "URL":
            url = declared
        elif resolver_url:
            url = resolver_url
        else:
            return {"status": "BLOCKED_NO_LIVE_RESOLVER_FOR_IDENTIFIER_TYPE", "source_exists": False,
                    "identifier_type": kind, "declared_identifier": declared, "resolver_owner": self.owner_id}
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return {"status": "REJECTED_NON_HTTPS_SOURCE", "source_exists": False,
                    "identifier_type": kind, "declared_identifier": declared, "resolver_owner": self.owner_id}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PhiCompiler/8.0 ScientificVerificationCore"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                final_url = response.geturl()
                raw = response.read(maximum_size_bytes + 1)
                if len(raw) > maximum_size_bytes:
                    raise ValueError("resolved source exceeds verification read limit")
                text = raw.decode("utf-8", errors="replace")
                low = text.casefold()
                title_ok = True if not expected_title else expected_title.casefold() in low
                if kind == "PMID":
                    id_ok = bool(re.search(rf"\b{re.escape(declared)}\b", text))
                elif kind == "DOI":
                    id_ok = True  # DOI resolver returning 2xx/redirect is the resolution event.
                else:
                    id_ok = True
                return {
                    "status": "RESOLVED_EXTERNAL_SOURCE" if id_ok and title_ok else "RESOLVED_BUT_BIBLIOGRAPHIC_MISMATCH",
                    "identifier_type": kind,
                    "declared_identifier": declared,
                    "resolved_identifier": declared,
                    "source_exists": True,
                    "bibliographic_match": bool(id_ok and title_ok),
                    "title": expected_title or "RESOLVED_EXTERNAL_SOURCE",
                    "resolved_url": final_url,
                    "retrieved_at": "LIVE_RUNTIME",
                    "retrieval_method": "LIVE_EXTERNAL_RESOLUTION",
                    "resolver_owner": self.owner_id,
                    "content_digest": hashlib.sha256(raw).hexdigest(),
                    "container": response.headers.get_content_type(),
                }
        except Exception as exc:
            return {
                "status": "BLOCKED_EXTERNAL_SOURCE_RESOLUTION_FAILED", "source_exists": False,
                "identifier_type": kind, "declared_identifier": declared,
                "resolver_owner": self.owner_id, "error_type": type(exc).__name__, "error": str(exc)[:400],
            }


class IndependentSourceVerifier:
    owner_id = SOURCE_VERIFIER_OWNER_ID

    def __init__(self, trusted_resolver_owners: Sequence[str] = ()) -> None:
        self.trusted_resolver_owners = set(DEFAULT_TRUSTED_RESOLVER_OWNERS) | {str(x) for x in trusted_resolver_owners}

    def verify(
        self, resolution: Mapping[str, Any], *, proposer_owner: str,
    ) -> Mapping[str, Any]:
        r = dict(resolution)
        kind = str(r.get("identifier_type", "OTHER")).upper()
        declared = _normalise_identifier(kind, r.get("declared_identifier"))
        resolved = _normalise_identifier(kind, r.get("resolved_identifier"))
        resolver_owner = str(r.get("resolver_owner", "")).strip()
        method = str(r.get("retrieval_method", "")).upper()
        checks = {
            "IDENTIFIER_TYPE_SUPPORTED": kind in SOURCE_IDENTIFIER_TYPES,
            "DECLARED_IDENTIFIER_PRESENT": bool(declared),
            "RESOLVED_IDENTIFIER_PRESENT": bool(resolved),
            "DECLARED_MATCHES_RESOLVED_IDENTIFIER": bool(declared and declared == resolved),
            "SOURCE_EXISTENCE_EXTERNALLY_RESOLVED": r.get("source_exists") is True,
            "BIBLIOGRAPHIC_MATCH_EXTERNALLY_RESOLVED": r.get("bibliographic_match") is True,
            "TITLE_RESOLVED": bool(str(r.get("title", "")).strip()),
            "RESOLVED_LOCATION_PRESENT": bool(str(r.get("resolved_url", "")).strip() or str(r.get("snapshot_path", "")).strip()),
            "CONTENT_DIGEST_VALID": _sha256_hex(r.get("content_digest")),
            "RETRIEVED_AT_DECLARED": bool(str(r.get("retrieved_at", "")).strip()),
            "RETRIEVAL_METHOD_TRUSTED": method in TRUSTED_RESOLUTION_METHODS,
            "RESOLVER_OWNER_TRUSTED": resolver_owner in self.trusted_resolver_owners,
            "RESOLVER_INDEPENDENT_FROM_PROPOSER": bool(resolver_owner) and resolver_owner != proposer_owner,
            "VERIFIER_INDEPENDENT_FROM_PROPOSER": self.owner_id != proposer_owner,
        }
        verified = all(checks.values())
        payload = {
            "schema": SOURCE_RECEIPT_SCHEMA, "owner_id": self.owner_id,
            "proposer_owner": proposer_owner, "resolver_owner": resolver_owner,
            "identifier_type": kind, "declared_identifier": declared, "resolved_identifier": resolved,
            "resolved_url": str(r.get("resolved_url", "")), "snapshot_path": str(r.get("snapshot_path", "")),
            "title": str(r.get("title", "")), "container": str(r.get("container", "")),
            "retrieved_at": str(r.get("retrieved_at", "")), "retrieval_method": method,
            "content_digest": str(r.get("content_digest", "")).lower(),
            "checks": checks, "verified": verified,
            "status": "VERIFIED_EXTERNAL_SOURCE" if verified else "REJECTED_UNVERIFIED_SOURCE",
            "claim_boundary": {
                "identifier_syntax_is_source_authenticity": False,
                "digest_is_authentication": False,
                "world_authorization_requires_world_tier_signature": True,
            },
        }
        receipt = dict(_receipt_digest(payload, "source_verification_digest"))
        return {**receipt, "source_receipt_id": "SVR-" + receipt["source_verification_digest"][:24].upper()}

    @staticmethod
    def receipt_valid(receipt: Mapping[str, Any], *, require_world_attestation: bool = False) -> bool:
        if receipt.get("schema") != SOURCE_RECEIPT_SCHEMA or receipt.get("owner_id") != SOURCE_VERIFIER_OWNER_ID:
            return False
        if receipt.get("verified") is not True or receipt.get("status") != "VERIFIED_EXTERNAL_SOURCE":
            return False
        body = dict(receipt); body.pop("source_receipt_id", None)
        if require_world_attestation and str(receipt.get("attestation_owner", "")).strip() != str(receipt.get("resolver_owner", "")).strip():
            return False
        return _attestation_valid(body, digest_key="source_verification_digest", required_role="SOURCE",
                                  required_tier=TRUST_TIER_WORLD if require_world_attestation else None)


class IndependentClaimVerifier:
    owner_id = CLAIM_VERIFIER_OWNER_ID

    def __init__(self, trusted_reviewer_owners: Sequence[str] = ()) -> None:
        self.trusted_reviewer_owners = set(DEFAULT_TRUSTED_REVIEWER_OWNERS) | {str(x) for x in trusted_reviewer_owners}

    def verify(
        self, source_receipt: Mapping[str, Any], claim_review: Mapping[str, Any], *, proposer_owner: str,
    ) -> Mapping[str, Any]:
        r = dict(claim_review)
        reviewer = str(r.get("reviewer_owner", "")).strip()
        relation = str(r.get("relation", "")).upper()
        method = str(r.get("review_method", "")).upper()
        checks = {
            "SOURCE_RECEIPT_VALID": IndependentSourceVerifier.receipt_valid(source_receipt),
            "CLAIM_FIELD_DECLARED": bool(str(r.get("claim_field", "")).strip()),
            "CLAIM_TEXT_DECLARED": bool(str(r.get("claim_text", "")).strip()),
            "RELATION_SUPPORTED": relation in CLAIM_RELATIONS,
            "FACT_SUMMARY_DECLARED": bool(str(r.get("fact_summary", "")).strip()),
            "LOCATOR_DECLARED": bool(str(r.get("locator", "")).strip()),
            "QUOTE_OR_PARAPHRASE_DECLARED": bool(str(r.get("quote_or_paraphrase", "")).strip()),
            "ENTAILMENT_INDEPENDENTLY_VERIFIED": r.get("entailment_verified") is True,
            "REVIEW_METHOD_TRUSTED": method in TRUSTED_REVIEW_METHODS,
            "REVIEWER_OWNER_TRUSTED": reviewer in self.trusted_reviewer_owners,
            "REVIEWER_INDEPENDENT_FROM_PROPOSER": bool(reviewer) and reviewer != proposer_owner,
            "REVIEWER_INDEPENDENT_FROM_RESOLVER": reviewer != str(source_receipt.get("resolver_owner", "")),
            "SOURCE_CONTENT_DIGEST_BOUND": str(r.get("source_content_digest", "")).lower() == str(source_receipt.get("content_digest", "")).lower(),
        }
        verified = all(checks.values())
        payload = {
            "schema": CLAIM_RECEIPT_SCHEMA, "owner_id": self.owner_id,
            "proposer_owner": proposer_owner, "reviewer_owner": reviewer, "review_method": method,
            "source_receipt_id": str(source_receipt.get("source_receipt_id", "")),
            "source_verification_digest": str(source_receipt.get("source_verification_digest", "")),
            "source_content_digest": str(source_receipt.get("content_digest", "")).lower(),
            "claim_field": str(r.get("claim_field", "")), "claim_value": r.get("claim_value"),
            "claim_text": str(r.get("claim_text", "")), "relation": relation,
            "fact_summary": str(r.get("fact_summary", "")), "locator": str(r.get("locator", "")),
            "quote_or_paraphrase": str(r.get("quote_or_paraphrase", "")), "context": str(r.get("context", "")),
            "checks": checks, "verified": verified,
            "status": "VERIFIED_SOURCE_CLAIM_LINK" if verified else "REJECTED_SOURCE_CLAIM_LINK",
        }
        receipt = dict(_receipt_digest(payload, "claim_verification_digest"))
        return {**receipt, "claim_receipt_id": "CVR-" + receipt["claim_verification_digest"][:24].upper()}

    @staticmethod
    def receipt_valid(
        receipt: Mapping[str, Any], source_receipts_by_id: Mapping[str, Mapping[str, Any]], *,
        require_world_attestation: bool = False,
    ) -> bool:
        if receipt.get("schema") != CLAIM_RECEIPT_SCHEMA or receipt.get("owner_id") != CLAIM_VERIFIER_OWNER_ID:
            return False
        if receipt.get("verified") is not True or receipt.get("status") != "VERIFIED_SOURCE_CLAIM_LINK":
            return False
        body = dict(receipt); body.pop("claim_receipt_id", None)
        if require_world_attestation and str(receipt.get("attestation_owner", "")).strip() != str(receipt.get("reviewer_owner", "")).strip():
            return False
        if not _attestation_valid(body, digest_key="claim_verification_digest", required_role="CLAIM",
                                  required_tier=TRUST_TIER_WORLD if require_world_attestation else None):
            return False
        source = source_receipts_by_id.get(str(receipt.get("source_receipt_id", "")))
        if source is None or not IndependentSourceVerifier.receipt_valid(source, require_world_attestation=require_world_attestation):
            return False
        return (
            str(receipt.get("source_verification_digest", "")) == str(source.get("source_verification_digest", ""))
            and str(receipt.get("source_content_digest", "")).lower() == str(source.get("content_digest", "")).lower()
        )


class IndependentArtifactVerifier:
    owner_id = ARTIFACT_VERIFIER_OWNER_ID
    allowed_classes = {"INTERNAL_MEASUREMENT", "LOCAL_SNAPSHOT", "MODEL_DERIVED", "SYNTHETIC_CONTROL", "QUALIFICATION_FIXTURE"}

    def __init__(self, trusted_verifier_owners: Sequence[str] = ()) -> None:
        self.trusted_verifier_owners = set(DEFAULT_TRUSTED_ARTIFACT_VERIFIER_OWNERS) | {str(x) for x in trusted_verifier_owners}

    def verify(
        self, artifact: Mapping[str, Any], *, proposer_owner: str,
    ) -> Mapping[str, Any]:
        a = dict(artifact)
        cls = str(a.get("artifact_class", "")).upper()
        verifier = str(a.get("verifier_owner", "")).strip()
        producer = str(a.get("producer_owner", "")).strip()
        checks = {
            "ARTIFACT_ID_DECLARED": bool(str(a.get("artifact_id", "")).strip()),
            "ARTIFACT_CLASS_SUPPORTED": cls in self.allowed_classes,
            "CONTENT_DIGEST_VALID": _sha256_hex(a.get("content_digest")),
            "PROVENANCE_DECLARED": bool(str(a.get("provenance", "")).strip()),
            "PRODUCER_OWNER_DECLARED": bool(producer),
            "VERIFIER_OWNER_TRUSTED": verifier in self.trusted_verifier_owners,
            "VERIFIER_INDEPENDENT_FROM_PRODUCER": bool(verifier) and verifier != producer,
            "VERIFIER_INDEPENDENT_FROM_PROPOSER": bool(verifier) and verifier != proposer_owner,
        }
        verified = all(checks.values())
        payload = {
            "schema": ARTIFACT_RECEIPT_SCHEMA, "owner_id": self.owner_id,
            "proposer_owner": proposer_owner, "verifier_owner": verifier,
            "artifact_id": str(a.get("artifact_id", "")), "artifact_class": cls,
            "producer_owner": producer, "content_digest": str(a.get("content_digest", "")).lower(),
            "provenance": str(a.get("provenance", "")),
            "independent_from_candidate_fit": bool(a.get("independent_from_candidate_fit", False)),
            "checks": checks, "verified": verified,
            "status": "VERIFIED_CONTENT_ADDRESSED_ARTIFACT" if verified else "REJECTED_UNVERIFIED_ARTIFACT",
        }
        receipt = dict(_receipt_digest(payload, "artifact_verification_digest"))
        return {**receipt, "artifact_receipt_id": "AVR-" + receipt["artifact_verification_digest"][:24].upper()}

    @staticmethod
    def receipt_valid(receipt: Mapping[str, Any], *, require_world_attestation: bool = False) -> bool:
        if receipt.get("schema") != ARTIFACT_RECEIPT_SCHEMA or receipt.get("owner_id") != ARTIFACT_VERIFIER_OWNER_ID:
            return False
        if receipt.get("verified") is not True or receipt.get("status") != "VERIFIED_CONTENT_ADDRESSED_ARTIFACT":
            return False
        body = dict(receipt); body.pop("artifact_receipt_id", None)
        if require_world_attestation and str(receipt.get("attestation_owner", "")).strip() != str(receipt.get("verifier_owner", "")).strip():
            return False
        return _attestation_valid(body, digest_key="artifact_verification_digest", required_role="ARTIFACT",
                                  required_tier=TRUST_TIER_WORLD if require_world_attestation else None)


class ScientificVerificationCore:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA, "owner_id": OWNER_ID,
            "sole_owner_of_generic_scientific_verification_rules": True,
            "pipeline": [
                "SEMANTIC_NULL", "SOURCE_AUTHENTICITY", "CRYPTOGRAPHIC_ATTESTATION",
                "BIBLIOGRAPHIC_MATCH", "CLAIM_SOURCE_ENTAILMENT", "CLAIM_VALUE_BINDING",
                "SOURCE_LOCK", "CONTRADICTION_ACCOUNTING", "ENTITY_IDENTITY",
                "EVIDENCE_CLASS", "CLAIM_BOUNDARY", "AUDIT_RECEIPT",
            ],
            "hard_invariants": {
                "bibliographic_identifier_string_is_verified_source": False,
                "digest_is_source_authentication": False,
                "world_receipt_requires_nonshipped_private_key_attestation": True,
                "non_insufficient_claim_without_verified_source_allowed": False,
                "ambiguous_without_verified_support_and_contradiction_allowed": False,
                "context_dependent_without_verified_context_allowed": False,
                "claim_receipt_for_different_value_may_satisfy_field": False,
                "unresolved_external_entity_is_scientific_candidate": False,
                "synthetic_or_qualification_fixture_is_world_evidence": False,
                "domain_owner_may_override_verification_failure": False,
                "serialized_verification_receipt_is_authorization_token": False,
                "runtime_contains_world_private_signing_key": False,
                "world_source_and_claim_attestors_may_share_key": False,
                "world_trust_store_may_accept_unbound_signer_owner": False,
            },
            "claim_relations": sorted(CLAIM_RELATIONS),
            "entity_resolution_states": sorted(ENTITY_RESOLUTION_STATES),
            "world_trust_configuration": {
                "active_world_public_key_count": sum(
                    1 for row in load_trust_store().get("keys", {}).values()
                    if str(row.get("trust_tier", "")).upper() == TRUST_TIER_WORLD
                ),
                "world_private_keys_shipped": False,
                "world_signing_api_exposed_by_runtime": False,
                "external_independent_verifier_service_required": True,
            },
            "claim_boundary": {
                "cryptographic_signature_authenticates_declared_verifier_key_not_world_truth_itself": True,
                "external_resolution_or_trusted_ingestion_still_required": True,
                "verification_pass_is_scientific_promotion": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _field_policy(value: Any, receipts: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        if semantic_state(value) != "USABLE":
            return {"declared_value": value, "adjudicated_value": "INSUFFICIENT", "source_lock_pass": True,
                    "status_consistent": True, "relations": [], "reason": "SEMANTIC_NULL_OR_MISSING_REQUIRES_NO_SOURCE"}
        token = normalize_status(value)
        relations = [str(r.get("relation", "")).upper() for r in receipts]
        support, contradict, qualify = relations.count("SUPPORTS"), relations.count("CONTRADICTS"), relations.count("QUALIFIES")
        contexts = [str(r.get("context", "")).strip() for r in receipts if str(r.get("context", "")).strip()]
        source_lock, adjudicated, consistent, reason = bool(receipts), value, True, "SOURCE_LOCK_SATISFIED"
        if token == "SUPPORTED":
            if support < 1:
                source_lock, adjudicated, reason = False, "INSUFFICIENT", "SUPPORTED_REQUIRES_VERIFIED_SUPPORT"
            elif contradict:
                adjudicated, consistent, reason = "AMBIGUOUS", False, "VERIFIED_CONTRADICTION_FORCES_AMBIGUOUS"
        elif token == "AMBIGUOUS":
            if support < 1 or contradict < 1:
                source_lock, adjudicated, reason = False, "INSUFFICIENT", "AMBIGUOUS_REQUIRES_SUPPORT_AND_CONTRADICTION"
        elif token == "CONTEXT_DEPENDENT":
            if support < 1 or (contradict + qualify) < 1 or not contexts:
                source_lock, adjudicated, reason = False, "INSUFFICIENT", "CONTEXT_DEPENDENT_REQUIRES_SUPPORT_QUALIFICATION_AND_CONTEXT"
        elif token == "CONTRADICTED":
            if contradict < 1:
                source_lock, adjudicated, reason = False, "INSUFFICIENT", "CONTRADICTED_REQUIRES_VERIFIED_CONTRADICTION"
        elif support < 1:
            source_lock, adjudicated, reason = False, "INSUFFICIENT", "NONTRIVIAL_VALUE_REQUIRES_VERIFIED_SUPPORT"
        return {
            "declared_value": value, "adjudicated_value": adjudicated, "source_lock_pass": source_lock,
            "status_consistent": consistent, "relations": relations, "support_count": support,
            "contradiction_count": contradict, "qualification_count": qualify, "context_count": len(contexts),
            "reason": reason,
        }

    def verify_bundle(
        self, bundle: Mapping[str, Any] | None, *, required_entity_slots: Sequence[str] = (),
        allowed_entity_states: Mapping[str, Sequence[str]] | None = None,
    ) -> Mapping[str, Any]:
        b = dict(bundle or {})
        proposer = str(b.get("proposer_owner", "")).strip()
        evidence_class = str(b.get("evidence_class", "EXTERNAL_SOURCE")).upper()
        claim_values = dict(b.get("claim_values", {}))
        source_receipts = [dict(x) for x in b.get("source_receipts", ())]
        claim_receipts = [dict(x) for x in b.get("claim_receipts", ())]
        artifact_receipts = [dict(x) for x in b.get("artifact_receipts", ())]
        entities = [dict(x) for x in b.get("entities", ())]
        minimum_distinct_sources = max(int(b.get("minimum_distinct_sources", b.get("minimum_independent_sources", 0)) or 0), 0)
        required_artifact_ids = {str(x) for x in b.get("required_artifact_ids", ())}

        source_by_id = {str(r.get("source_receipt_id", "")): r for r in source_receipts if str(r.get("source_receipt_id", ""))}
        source_results: dict[str, Any] = {}
        for sid, r in source_by_id.items():
            valid = IndependentSourceVerifier.receipt_valid(r) and str(r.get("proposer_owner", "")) == proposer
            source_results[sid] = {
                "valid": valid, "world_attested": IndependentSourceVerifier.receipt_valid(r, require_world_attestation=True),
                "proposer_match": str(r.get("proposer_owner", "")) == proposer,
                "identifier_type": r.get("identifier_type"), "resolved_identifier": r.get("resolved_identifier"),
                "trust_tier": receipt_trust_tier(r),
            }

        valid_claims, invalid_claim_ids = [], []
        for r in claim_receipts:
            rid = str(r.get("claim_receipt_id", "")) or "UNIDENTIFIED_CLAIM_RECEIPT"
            if IndependentClaimVerifier.receipt_valid(r, source_by_id) and str(r.get("proposer_owner", "")) == proposer:
                valid_claims.append(r)
            else:
                invalid_claim_ids.append(rid)
        valid_artifacts = [r for r in artifact_receipts if IndependentArtifactVerifier.receipt_valid(r) and str(r.get("proposer_owner", "")) == proposer]
        invalid_artifact_ids = [str(r.get("artifact_id", "")) or "UNIDENTIFIED_ARTIFACT" for r in artifact_receipts if r not in valid_artifacts]
        valid_artifact_ids = {str(r.get("artifact_id", "")) for r in valid_artifacts}

        field_results, sanitized, source_lock_failures, status_mismatches = {}, {}, [], []
        for field, value in claim_values.items():
            field_claims = [r for r in valid_claims if str(r.get("claim_field", "")) == str(field)]
            linked = [r for r in field_claims if digest_payload(r.get("claim_value")) == digest_payload(value)]
            mismatch = [r.get("claim_receipt_id") for r in field_claims if r not in linked]
            result = dict(self._field_policy(value, linked))
            result["verified_claim_receipt_ids"] = [r.get("claim_receipt_id") for r in linked]
            result["claim_value_mismatch_receipt_ids"] = mismatch
            if semantic_state(value) == "USABLE" and mismatch and not linked:
                result.update(source_lock_pass=False, adjudicated_value="INSUFFICIENT",
                              reason="CLAIM_RECEIPT_VALUE_NOT_BOUND_TO_DECLARED_FIELD_VALUE")
            field_results[str(field)] = result
            sanitized[str(field)] = result["adjudicated_value"]
            if not result["source_lock_pass"]:
                source_lock_failures.append(str(field))
            if not result["status_consistent"]:
                status_mismatches.append(str(field))

        entity_by_slot = {str(e.get("entity_slot", "")): e for e in entities if str(e.get("entity_slot", ""))}
        allowed_map = {str(k): {str(v).upper() for v in vals} for k, vals in dict(allowed_entity_states or {}).items()}
        entity_results, identity_failures, synthetic_controls = {}, [], []
        for slot in [str(x) for x in required_entity_slots]:
            e = entity_by_slot.get(slot)
            if e is None:
                entity_results[slot] = {"status": "FAIL", "reason": "REQUIRED_ENTITY_IDENTITY_RECEIPT_MISSING"}
                identity_failures.append(slot); continue
            state = str(e.get("resolution_status", "UNRESOLVED")).upper()
            if state not in ENTITY_RESOLUTION_STATES:
                state = "UNRESOLVED"
            ids = {str(x) for x in e.get("identity_claim_receipt_ids", ())}
            id_claims = [r for r in valid_claims if str(r.get("claim_receipt_id", "")) in ids and str(r.get("relation", "")) == "IDENTIFIES"]
            if state == "ESTABLISHED_EXTERNAL":
                ok = bool(str(e.get("canonical_identifier", "")).strip()) and bool(id_claims)
                reason = "EXTERNAL_ENTITY_IDENTITY_VERIFIED" if ok else "EXTERNAL_ENTITY_NOT_RESOLVED_BY_VERIFIED_SOURCE"
            elif state == "DEFINED_INTERNAL":
                definition = str(e.get("definition", "")).strip()
                ok = bool(definition) and str(e.get("definition_digest", "")) == digest_payload({"definition": definition})
                reason = "INTERNAL_CONSTRUCT_DEFINITION_VERIFIED_NOT_WORLD_ENTITY" if ok else "INTERNAL_CONSTRUCT_DEFINITION_INVALID"
            elif state == "SYNTHETIC_CONTROL":
                ok, reason = True, "SYNTHETIC_CONTROL_VALID_FOR_TESTING_NOT_SCIENTIFIC_CANDIDATE"
                synthetic_controls.append(slot)
            else:
                ok, reason = False, "ENTITY_UNRESOLVED"
            if slot in allowed_map and state not in allowed_map[slot]:
                ok, reason = False, "ENTITY_RESOLUTION_STATE_NOT_ALLOWED_FOR_DOMAIN_PATH"
            entity_results[slot] = {
                "status": "PASS" if ok else "FAIL", "reason": reason,
                "label": e.get("label"), "entity_kind": e.get("entity_kind"),
                "resolution_status": state, "canonical_identifier": e.get("canonical_identifier"),
                "identity_claim_receipt_ids": [r.get("claim_receipt_id") for r in id_claims],
            }
            if not ok:
                identity_failures.append(slot)

        distinct_sources = {
            (str(r.get("identifier_type", "")), str(r.get("resolved_identifier", "")))
            for sid, r in source_by_id.items() if source_results.get(sid, {}).get("valid")
        }
        all_source_valid = all(x["valid"] for x in source_results.values()) if source_results else True
        external_ok = evidence_class != "EXTERNAL_SOURCE" or (bool(source_by_id) and bool(valid_claims))
        internal_classes = {"INTERNAL_MEASUREMENT", "LOCAL_SNAPSHOT", "MODEL_DERIVED", "SYNTHETIC_CONTROL", "QUALIFICATION_FIXTURE"}
        internal_ok = evidence_class not in internal_classes or (bool(valid_artifacts) and required_artifact_ids.issubset(valid_artifact_ids))
        source_key_ids = {str(r.get("attestation_key_id", "")) for r in source_by_id.values() if str(r.get("attestation_key_id", ""))}
        claim_key_ids = {str(r.get("attestation_key_id", "")) for r in valid_claims if str(r.get("attestation_key_id", ""))}
        source_claim_attestors_distinct = not (source_key_ids & claim_key_ids)
        world_key_count = sum(
            1 for row in load_trust_store().get("keys", {}).values()
            if str(row.get("trust_tier", "")).upper() == TRUST_TIER_WORLD
        )
        generic_checks = {
            "PROPOSER_OWNER_DECLARED": bool(proposer),
            "ALL_REFERENCED_SOURCE_RECEIPTS_VALID": all_source_valid,
            "ALL_CLAIM_RECEIPTS_VALID": not invalid_claim_ids,
            "ALL_ARTIFACT_RECEIPTS_VALID": not invalid_artifact_ids,
            "REQUIRED_ARTIFACTS_VERIFIED": required_artifact_ids.issubset(valid_artifact_ids),
            "EXTERNAL_SOURCE_HAS_VERIFIED_SOURCE_AND_CLAIM": external_ok,
            "MINIMUM_DISTINCT_VERIFIED_SOURCE_COUNT": len(distinct_sources) >= minimum_distinct_sources,
            "INTERNAL_EVIDENCE_HAS_CONTENT_ADDRESSED_ARTIFACT": internal_ok,
            "SOURCE_LOCK_ALL_NONTRIVIAL_FIELDS": not source_lock_failures,
            "REQUIRED_ENTITY_IDENTITIES_RESOLVED": not identity_failures,
            "NO_SYNTHETIC_CONTROL_IN_SCIENTIFIC_CANDIDATE_PATH": not synthetic_controls,
            "SOURCE_AND_CLAIM_ATTESTATION_KEYS_DISTINCT": source_claim_attestors_distinct,
        }
        evidence_ready = all(generic_checks.values())

        qualification_source = any(receipt_trust_tier(r) == TRUST_TIER_QUALIFICATION for r in source_by_id.values())
        qualification_artifact = any(receipt_trust_tier(r) == TRUST_TIER_QUALIFICATION for r in valid_artifacts)
        all_sources_world = all(IndependentSourceVerifier.receipt_valid(r, require_world_attestation=True) for r in source_by_id.values()) if source_by_id else True
        all_claims_world = all(IndependentClaimVerifier.receipt_valid(r, source_by_id, require_world_attestation=True) for r in valid_claims) if valid_claims else True
        all_artifacts_world = all(IndependentArtifactVerifier.receipt_valid(r, require_world_attestation=True) for r in valid_artifacts) if valid_artifacts else True
        world_attestation_ready = (
            world_key_count > 0
            and source_claim_attestors_distinct
            and (evidence_class != "EXTERNAL_SOURCE" or (all_sources_world and all_claims_world))
            and (evidence_class not in {"INTERNAL_MEASUREMENT", "LOCAL_SNAPSHOT"} or all_artifacts_world)
        )
        world_class = evidence_class not in {"SYNTHETIC_CONTROL", "QUALIFICATION_FIXTURE", "MODEL_DERIVED"}
        scientific_candidate_allowed = evidence_ready and not synthetic_controls and world_class and world_attestation_ready and not qualification_source and not qualification_artifact

        if identity_failures:
            overall = "FAIL_ENTITY_IDENTITY_UNRESOLVED"
        elif synthetic_controls:
            overall = "REJECT_SYNTHETIC_CONTROL_FROM_SCIENTIFIC_CANDIDATE"
        elif source_lock_failures or invalid_claim_ids or not all_source_valid:
            overall = "FAIL_EVIDENCE_SOURCE_VERIFICATION"
        elif not evidence_ready:
            overall = "FAIL_SCIENTIFIC_VERIFICATION_PRECONDITION"
        elif not scientific_candidate_allowed:
            overall = "PASS_ENGINE_OR_MODEL_VERIFICATION_WORLD_CLAIM_BLOCKED"
        elif status_mismatches:
            overall = "PASS_WITH_VERIFIED_EVIDENCE_ADJUDICATION"
        else:
            overall = "PASS_SCIENTIFIC_VERIFICATION_PRECONDITION"

        payload = {
            "schema": VERIFICATION_RECEIPT_SCHEMA, "owner_id": OWNER_ID,
            "proposer_owner": proposer, "evidence_class": evidence_class,
            "generic_checks": generic_checks, "source_results": source_results,
            "invalid_claim_receipt_ids": invalid_claim_ids, "invalid_artifact_ids": invalid_artifact_ids,
            "verified_artifact_ids": sorted(valid_artifact_ids), "minimum_distinct_sources": minimum_distinct_sources,
            "field_results": field_results, "sanitized_claim_values": sanitized,
            "source_lock_failures": source_lock_failures, "status_mismatches": status_mismatches,
            "entity_results": entity_results, "identity_failures": identity_failures,
            "synthetic_control_slots": synthetic_controls, "evidence_ready_for_domain": evidence_ready,
            "world_attestation_ready": world_attestation_ready,
            "world_trust_key_count": world_key_count,
            "source_claim_attestation_keys_distinct": source_claim_attestors_distinct,
            "scientific_candidate_allowed": scientific_candidate_allowed,
            "overall_status": overall,
            "claim_boundary": {
                "verification_is_scientific_promotion": False,
                "serialized_receipt_is_authorization_token": False,
                "world_novelty_established": False,
                "clinical_or_physical_truth_established": False,
                "unverified_evidence_value_used_downstream": False,
            },
        }
        receipt = dict(_receipt_digest(payload, "verification_digest"))
        return {**receipt, "verification_receipt_id": "SCI-VER-" + receipt["verification_digest"][:24].upper()}

    @staticmethod
    def receipt_integrity_valid(receipt: Mapping[str, Any] | None) -> bool:
        if not isinstance(receipt, Mapping) or receipt.get("schema") != VERIFICATION_RECEIPT_SCHEMA or receipt.get("owner_id") != OWNER_ID:
            return False
        body = dict(receipt); body.pop("verification_receipt_id", None)
        return _receipt_digest_valid(body, "verification_digest")


def build_qualification_source_receipt(
    *, identifier_type: str, identifier: str, title: str, content_text: str,
    proposer_owner: str, resolved_url: str = "https://qualification.invalid/source",
) -> Mapping[str, Any]:
    resolution = {
        "identifier_type": identifier_type, "declared_identifier": identifier, "resolved_identifier": identifier,
        "source_exists": True, "bibliographic_match": True, "title": title, "resolved_url": resolved_url,
        "retrieved_at": "QUALIFICATION_FIXTURE", "retrieval_method": "QUALIFICATION_FIXTURE",
        "resolver_owner": "SCIENTIFIC-VERIFICATION-QUALIFICATION",
        "content_digest": hashlib.sha256(content_text.encode("utf-8")).hexdigest(), "container": "QUALIFICATION_FIXTURE",
    }
    unsigned = IndependentSourceVerifier().verify(resolution, proposer_owner=proposer_owner)
    body = dict(unsigned); body.pop("source_receipt_id", None)
    signed = _attest_receipt(
        body, digest_key="source_verification_digest", private_key=_qualification_private_key("SOURCE"),
        key_id=QUALIFICATION_SOURCE_KEY_ID, attestation_owner="SCIENTIFIC-VERIFICATION-QUALIFICATION",
    )
    return {**signed, "source_receipt_id": "SVR-" + signed["source_verification_digest"][:24].upper()}


def build_qualification_claim_receipt(
    source_receipt: Mapping[str, Any], *, claim_field: str, claim_value: Any, relation: str,
    claim_text: str, fact_summary: str, proposer_owner: str, context: str = "",
) -> Mapping[str, Any]:
    review = {
        "reviewer_owner": "SCIENTIFIC-VERIFICATION-QUALIFICATION-REVIEWER",
        "review_method": "QUALIFICATION_FIXTURE", "claim_field": claim_field, "claim_value": claim_value,
        "claim_text": claim_text, "relation": relation, "fact_summary": fact_summary,
        "locator": "QUALIFICATION_FIXTURE", "quote_or_paraphrase": fact_summary, "context": context,
        "entailment_verified": True, "source_content_digest": source_receipt.get("content_digest"),
    }
    unsigned = IndependentClaimVerifier().verify(source_receipt, review, proposer_owner=proposer_owner)
    body = dict(unsigned); body.pop("claim_receipt_id", None)
    signed = _attest_receipt(
        body, digest_key="claim_verification_digest", private_key=_qualification_private_key("CLAIM"),
        key_id=QUALIFICATION_CLAIM_KEY_ID, attestation_owner="SCIENTIFIC-VERIFICATION-QUALIFICATION-REVIEWER",
    )
    return {**signed, "claim_receipt_id": "CVR-" + signed["claim_verification_digest"][:24].upper()}


def build_qualification_artifact_receipt(
    *, artifact_id: str, content: Any, proposer_owner: str, producer_owner: str = "QUALIFICATION-HARNESS",
    artifact_class: str = "QUALIFICATION_FIXTURE",
) -> Mapping[str, Any]:
    artifact = {
        "artifact_id": artifact_id, "artifact_class": artifact_class,
        "producer_owner": producer_owner, "verifier_owner": "SCIENTIFIC-VERIFICATION-QUALIFICATION-ARTIFACT",
        "content_digest": content_addressed_digest(content),
        "provenance": "QUALIFICATION_FIXTURE", "independent_from_candidate_fit": True,
    }
    unsigned = IndependentArtifactVerifier().verify(artifact, proposer_owner=proposer_owner)
    body = dict(unsigned); body.pop("artifact_receipt_id", None)
    signed = _attest_receipt(
        body, digest_key="artifact_verification_digest", private_key=_qualification_private_key("ARTIFACT"),
        key_id=QUALIFICATION_ARTIFACT_KEY_ID, attestation_owner="SCIENTIFIC-VERIFICATION-QUALIFICATION-ARTIFACT",
    )
    return {**signed, "artifact_receipt_id": "AVR-" + signed["artifact_verification_digest"][:24].upper()}


__all__ = [
    "OWNER_ID", "SOURCE_RESOLVER_OWNER_ID", "SOURCE_VERIFIER_OWNER_ID", "CLAIM_VERIFIER_OWNER_ID",
    "ARTIFACT_VERIFIER_OWNER_ID", "SCHEMA", "SOURCE_RECEIPT_SCHEMA", "CLAIM_RECEIPT_SCHEMA",
    "ARTIFACT_RECEIPT_SCHEMA", "VERIFICATION_RECEIPT_SCHEMA", "TRUST_STORE_SCHEMA",
    "TRUST_TIER_WORLD", "TRUST_TIER_QUALIFICATION", "semantic_state", "is_usable",
    "normalize_status", "gate", "content_addressed_digest", "load_trust_store", "receipt_trust_tier",
    "ExternalSourceResolutionOwner", "IndependentSourceVerifier", "IndependentClaimVerifier",
    "IndependentArtifactVerifier", "ScientificVerificationCore", "build_qualification_source_receipt",
    "build_qualification_claim_receipt", "build_qualification_artifact_receipt",
]
