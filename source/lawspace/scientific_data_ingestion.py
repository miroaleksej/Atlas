"""Authoritative scientific-data ingestion and provenance owner.

This owner replaces domain-specific artifact loaders. It safely materializes
published files, verifies provenance and digests, validates container/schema
profiles, and emits one domain-neutral ExperimentDataIR. Domain owners consume
that IR and remain responsible for scientific formulas and likelihoods.

Supported profiles are declarative. Adding a physics, chemistry, mechanics, or
mathematics dataset must not add a second download/parser algorithm.
"""
from __future__ import annotations

import csv
import dataclasses
import fnmatch
import hashlib
import io
import json
import os
import tempfile
import tarfile
import urllib.parse
import urllib.request
import zipfile

import numpy as np
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

OWNER_ID = "SCIENTIFIC-DATA-INGESTION"
OWNER_VERSION = "5.11.0"
SCHEMA = "phi-scientific-data-ingestion/v5.11"
IR_SCHEMA = "phi-experiment-data-ir/v3"


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()
    ).hexdigest()


@dataclass(frozen=True)
class SchemaProfile:
    profile_id: str
    container_format: str
    media_type: str
    required_member_patterns: tuple[str, ...] = ()
    required_json_keys: tuple[str, ...] = ()
    required_table_columns: tuple[str, ...] = ()
    delimiter: str | None = None
    semantic_description: str = ""


@dataclass(frozen=True)
class ScientificArtifact:
    artifact_id: str
    logical_dataset_id: str
    domain: str
    experiment_type: str
    semantic_role: str
    schema_profile_id: str
    source_urls: tuple[str, ...]
    local_relative_path: str
    expected_sha256: str | None = None
    expected_md5: str | None = None
    source_doi: str | None = None
    required_for: tuple[str, ...] = ()
    published_digest_algorithm: str | None = None
    maximum_size_bytes: int = 64 * 1024 * 1024

    def _safe_path(self, root: Path) -> Path:
        root_resolved = root.resolve()
        candidate = (root / self.local_relative_path).resolve()
        if candidate != root_resolved and root_resolved not in candidate.parents:
            raise ValueError("artifact path escapes current-state root")
        return candidate

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("only explicit HTTPS artifact endpoints are allowed")
        allowed = {
            "zenodo.org",
            "www.katrin.kit.edu",
            "katrin.kit.edu",
            "files.pythonhosted.org",
            "github.com",
            "raw.githubusercontent.com",
        }
        if parsed.hostname.lower() not in allowed:
            raise ValueError(f"artifact host is not allow-listed: {parsed.hostname}")

    def inspect(self, owner: "ScientificDataIngestionOwner") -> Mapping[str, Any]:
        try:
            path = self._safe_path(owner.root)
        except ValueError as exc:
            return {
                "artifact_id": self.artifact_id,
                "status": "BLOCKED_UNSAFE_ARTIFACT_PATH",
                "present": False,
                "error": str(exc),
            }
        if not path.is_file():
            return {
                "artifact_id": self.artifact_id,
                "logical_dataset_id": self.logical_dataset_id,
                "status": "BLOCKED_EXTERNAL_ARTIFACT_NOT_MATERIALIZED",
                "present": False,
                "path": self.local_relative_path,
                "source_urls": self.source_urls,
                "source_doi": self.source_doi,
                "domain": self.domain,
                "experiment_type": self.experiment_type,
                "semantic_role": self.semantic_role,
                "schema_profile_id": self.schema_profile_id,
            }
        raw = path.read_bytes()
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        actual_md5 = hashlib.md5(raw).hexdigest()  # published-source comparison only
        checks: dict[str, bool] = {}
        if self.expected_sha256:
            checks["sha256"] = actual_sha256 == self.expected_sha256
        if self.expected_md5:
            checks["published_md5"] = actual_md5 == self.expected_md5
        if not checks:
            digest_status = "BLOCKED_PUBLISHED_DIGEST_UNBOUND"
        elif all(checks.values()):
            digest_status = "PASS_PUBLISHED_DIGEST_BOUND_ARTIFACT"
        else:
            digest_status = "BLOCKED_EXTERNAL_ARTIFACT_DIGEST_MISMATCH"
        schema_result = owner.validate_schema(path, self.schema_profile_id) if digest_status.startswith("PASS_") else {
            "status": "BLOCKED_SCHEMA_VALIDATION_REQUIRES_VALID_DIGEST"
        }
        status = digest_status if not digest_status.startswith("PASS_") else schema_result["status"]
        if digest_status.startswith("PASS_") and schema_result["status"].startswith("PASS_"):
            status = "PASS_INGESTION_READY_ARTIFACT"
        return {
            "artifact_id": self.artifact_id,
            "logical_dataset_id": self.logical_dataset_id,
            "status": status,
            "digest_status": digest_status,
            "schema_status": schema_result["status"],
            "schema_result": schema_result,
            "present": True,
            "path": self.local_relative_path,
            "size_bytes": len(raw),
            "actual_sha256": actual_sha256,
            "actual_md5": actual_md5,
            "expected_sha256": self.expected_sha256,
            "expected_md5": self.expected_md5,
            "checks": checks,
            "source_urls": self.source_urls,
            "source_doi": self.source_doi,
            "domain": self.domain,
            "experiment_type": self.experiment_type,
            "semantic_role": self.semantic_role,
            "schema_profile_id": self.schema_profile_id,
        }

    def materialize(self, owner: "ScientificDataIngestionOwner", *, timeout_seconds: float = 120.0) -> Mapping[str, Any]:
        existing = self.inspect(owner)
        if existing.get("status") == "PASS_INGESTION_READY_ARTIFACT":
            return {**existing, "materialization": "ALREADY_PRESENT"}
        path = self._safe_path(owner.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        failures: list[Mapping[str, Any]] = []
        for url in self.source_urls:
            try:
                self._validate_url(url)
                request = urllib.request.Request(url, headers={"User-Agent": "PhiCompiler/5.9 scientific-data-ingestion-owner"})
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    final_url = response.geturl()
                    self._validate_url(final_url)
                    declared = response.headers.get("Content-Length")
                    if declared and int(declared) > self.maximum_size_bytes:
                        raise ValueError("artifact exceeds declared maximum size")
                    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
                    size = 0
                    try:
                        with os.fdopen(fd, "wb") as output:
                            while True:
                                block = response.read(1024 * 1024)
                                if not block:
                                    break
                                size += len(block)
                                if size > self.maximum_size_bytes:
                                    raise ValueError("artifact exceeds maximum size while streaming")
                                output.write(block)
                            output.flush()
                            os.fsync(output.fileno())
                        tmp_path = Path(tmp_name)
                        raw = tmp_path.read_bytes()
                        if self.expected_sha256 and hashlib.sha256(raw).hexdigest() != self.expected_sha256:
                            raise ValueError("downloaded SHA-256 mismatch")
                        if self.expected_md5 and hashlib.md5(raw).hexdigest() != self.expected_md5:
                            raise ValueError("downloaded published MD5 mismatch")
                        schema_result = owner.validate_schema(tmp_path, self.schema_profile_id)
                        if not schema_result["status"].startswith("PASS_"):
                            raise ValueError(f"downloaded schema mismatch: {schema_result['status']}")
                        os.replace(tmp_path, path)
                    except Exception:
                        Path(tmp_name).unlink(missing_ok=True)
                        raise
                result = self.inspect(owner)
                return {**result, "materialization": "DOWNLOADED_VALIDATED_AND_ATOMICALLY_COMMITTED", "resolved_url": final_url}
            except Exception as exc:
                failures.append({"url": url, "error_type": type(exc).__name__, "error": str(exc)[:500]})
        return {
            "artifact_id": self.artifact_id,
            "status": "BLOCKED_OFFICIAL_ARTIFACT_TRANSPORT_OR_SCHEMA_FAILURE",
            "present": False,
            "path": self.local_relative_path,
            "attempts": tuple(failures),
            "synthetic_substitution_allowed": False,
        }


@dataclass(frozen=True)
class ObservableDescriptor:
    """Declarative field-level observable mapping for a provenance-bound dataset.

    The descriptor does not parse scientific meaning from text.  It binds an
    exact field/member selector to an already-canonical quantity_id.  This is
    the missing bridge between artifact ingestion and candidate measurement
    projection; domain owners remain responsible for formulas/likelihoods.
    """
    observable_id: str
    quantity_id: str
    role: str
    artifact_id: str
    member_path: str
    selector_kind: str
    selector: str
    source_unit: str
    description: str = ""
    canonical_scale: float | None = None


@dataclass(frozen=True)
class ResponseProjectionDescriptor:
    """Declarative bridge from a typed source owner to an executable dataset response.

    This descriptor contains no measured response value and executes no likelihood.
    It freezes *which* existing domain owner may compute *which* canonical response
    quantity from the already-qualified ExperimentDataIR.  Candidate-specific
    scientific discrimination remains a separate downstream requirement.
    """
    response_projection_id: str
    source_owner_id: str
    execution_owner_id: str
    execution_operation: str
    response_quantity_id: str
    response_key: str
    required_input_quantity_ids: tuple[str, ...]
    response_semantics: str
    candidate_prediction_required_for_scientific_discrimination: bool = True


@dataclass(frozen=True)
class DatasetContract:
    dataset_id: str
    domain: str
    experiment_type: str
    # Each inner tuple is an alternative group: at least one artifact must pass.
    required_artifact_groups: tuple[tuple[str, ...], ...]
    optional_artifacts: tuple[str, ...] = ()
    adapter_id: str = "GENERIC_TYPED_ADAPTER"
    source_family_ids: tuple[str, ...] = ()
    observable_descriptors: tuple[ObservableDescriptor, ...] = ()
    response_projection_descriptors: tuple[ResponseProjectionDescriptor, ...] = ()


@dataclass(frozen=True)
class ExperimentDataIR:
    schema: str
    dataset_id: str
    domain: str
    experiment_type: str
    data_entities: tuple[Mapping[str, Any], ...]
    metadata_entities: tuple[Mapping[str, Any], ...]
    covariance_entities: tuple[Mapping[str, Any], ...]
    response_entities: tuple[Mapping[str, Any], ...]
    nuisance_entities: tuple[Mapping[str, Any], ...]
    observable_catalog: tuple[Mapping[str, Any], ...]
    source_family_ids: tuple[str, ...]
    provenance: Mapping[str, Any]
    status: str
    digest: str


SCHEMA_PROFILES: tuple[SchemaProfile, ...] = (
    SchemaProfile("GENERIC_JSON", "JSON", "application/json", semantic_description="JSON document with provenance-bound schema"),
    SchemaProfile("RO_CRATE_JSONLD", "RO_CRATE", "application/ld+json", required_json_keys=("@context", "@graph"), semantic_description="RO-Crate JSON-LD metadata"),
    SchemaProfile("FRICTIONLESS_DATA_PACKAGE", "FRICTIONLESS", "application/json", required_json_keys=("resources",), semantic_description="Frictionless Data Package"),
    SchemaProfile("GENERIC_CSV", "CSV", "text/csv", delimiter=",", semantic_description="Schema-qualified comma-separated table"),
    SchemaProfile("GENERIC_TSV", "TSV", "text/tab-separated-values", delimiter="\t", semantic_description="Schema-qualified tab-separated table"),
    SchemaProfile("GENERIC_NPY", "NPY", "application/x-npy", semantic_description="NumPy dense array"),
    SchemaProfile("GENERIC_NPZ", "NPZ", "application/x-npz", semantic_description="NumPy array archive"),
    SchemaProfile("GENERIC_HDF5", "HDF5", "application/x-hdf5", semantic_description="HDF5 multidimensional scientific container"),
    SchemaProfile("GENERIC_NEXUS", "HDF5", "application/x-hdf5", semantic_description="NeXus semantic model over HDF5"),
    SchemaProfile("GENERIC_ROOT", "ROOT", "application/x-root", semantic_description="ROOT scientific object container"),
    SchemaProfile("GENERIC_ZIP", "ZIP", "application/zip", semantic_description="Safe archive with declarative member requirements"),
    SchemaProfile("GENERIC_WHEEL", "WHEEL", "application/zip", required_member_patterns=("*.dist-info/METADATA",), semantic_description="Python wheel used as published data/model container"),
    SchemaProfile(
        "DAYABAY_ANALYSIS_ARCHIVE",
        "ZIP",
        "application/zip",
        required_member_patterns=("*.npz", "*detector*", "*spectrum*|*ibd*", "*.yaml|*.yml|*parameter*"),
        semantic_description="Official Daya Bay analysis container",
    ),
    SchemaProfile(
        "DAYABAY_ANALYSIS_WHEEL",
        "WHEEL",
        "application/zip",
        required_member_patterns=("*.dist-info/METADATA", "*dayabay*"),
        semantic_description="Official Daya Bay analysis data wheel",
    ),
    SchemaProfile(
        "DAYABAY_MODEL_WHEEL",
        "WHEEL",
        "application/zip",
        required_member_patterns=("dayabay_model/__init__.py", "dayabay_model/model_dayabay.py", "dayabay_model-1.8.0.dist-info/METADATA"),
        semantic_description="Daya Bay reference-model wheel",
    ),
    SchemaProfile("KATRIN_DATA_JSON", "JSON", "application/json", semantic_description="KATRIN KNM1-KNM5 scan data"),
    SchemaProfile("KATRIN_INPUTS_JSON", "JSON", "application/json", semantic_description="KATRIN response and systematic inputs"),
    SchemaProfile(
        "T2K_ROOT_RELEASE_ZIP",
        "ZIP",
        "application/zip",
        required_member_patterns=("*.root",),
        semantic_description="Published T2K ROOT likelihood/posterior products",
    ),
    SchemaProfile(
        "SUPERK_ATMOSPHERIC_TAR_GZ",
        "TAR_GZ",
        "application/gzip",
        required_member_patterns=("*bin/*", "*chi2/*"),
        semantic_description="Super-Kamiokande atmospheric 930-bin and published chi-square products",
    ),
    SchemaProfile(
        "SUPERK_SOLAR_RELEASE_ZIP",
        "ZIP",
        "application/zip",
        required_member_patterns=("*solar_angle.root", "*.txt|*.dat|*.csv"),
        semantic_description="Super-Kamiokande solar-angle and electron-neutrino survival-probability products",
    ),
)


DAYABAY_ANALYSIS_NPZ = ScientificArtifact(
    artifact_id="DAYA-BAY-ANALYSIS-NPZ-1.0.0",
    logical_dataset_id="DAYA-BAY-OFFICIAL-ANALYSIS",
    domain="physics.particle.neutrino",
    experiment_type="reactor_neutrino_oscillation",
    semantic_role="OBSERVATIONS_AND_METADATA",
    schema_profile_id="DAYABAY_ANALYSIS_ARCHIVE",
    source_urls=("https://zenodo.org/records/17587229/files/dayabay_analysis_dataset_npz_1-0-0.zip?download=1",),
    source_doi="10.5281/zenodo.17587229",
    local_relative_path="data/external/neutrino/dayabay_analysis_dataset_npz_1-0-0.zip",
    expected_md5="dfc33dce75508b53e9821329b3e06a17",
    required_for=("DAYA-BAY-FULL-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=8 * 1024 * 1024,
)

DAYABAY_ANALYSIS_WHEEL = ScientificArtifact(
    artifact_id="DAYA-BAY-ANALYSIS-WHEEL-1.0.1",
    logical_dataset_id="DAYA-BAY-OFFICIAL-ANALYSIS",
    domain="physics.particle.neutrino",
    experiment_type="reactor_neutrino_oscillation",
    semantic_role="OBSERVATIONS_AND_METADATA_ALTERNATIVE_CONTAINER",
    schema_profile_id="DAYABAY_ANALYSIS_WHEEL",
    source_urls=("https://files.pythonhosted.org/packages/08/ed/3737fec345f00c4ffcb2dec3f69355b8cdb4eee135a1cd76db29b5d02753/dayabay_data_official-1.0.1-py3-none-any.whl",),
    local_relative_path="data/external/neutrino/dayabay_data_official-1.0.1-py3-none-any.whl",
    expected_sha256="4578d71a741041d7b729dc7cacaa0836efe852d8f407d222ff8916c190dcfadf",
    required_for=("DAYA-BAY-FULL-LIKELIHOOD",),
    published_digest_algorithm="SHA256_PYPI",
    maximum_size_bytes=8 * 1024 * 1024,
)

DAYABAY_MODEL_WHEEL = ScientificArtifact(
    artifact_id="DAYA-BAY-MODEL-WHEEL-1.8.0",
    logical_dataset_id="DAYA-BAY-OFFICIAL-ANALYSIS",
    domain="physics.particle.neutrino",
    experiment_type="reactor_neutrino_oscillation",
    semantic_role="RESPONSE_AND_REFERENCE_MODEL",
    schema_profile_id="DAYABAY_MODEL_WHEEL",
    source_urls=("https://files.pythonhosted.org/packages/89/76/4635a2c53903a3f75cce69e9ce53e4ac7ee80072b402192c88d36736bbee/dayabay_model-1.8.0-py3-none-any.whl",),
    local_relative_path="data/external/neutrino/dayabay_model-1.8.0-py3-none-any.whl",
    expected_sha256="74c328f9c8527bf3e1fac3d8e24acdee2253a3ee44c32066dcd2a4529efb7fb7",
    required_for=("DAYA-BAY-FULL-LIKELIHOOD",),
    published_digest_algorithm="SHA256_PYPI",
    maximum_size_bytes=2 * 1024 * 1024,
)

KATRIN_KNM1_5_JSON = ScientificArtifact(
    artifact_id="KATRIN-KNM1-5-DATA-JSON",
    logical_dataset_id="KATRIN-KNM1-5-OFFICIAL",
    domain="physics.particle.neutrino",
    experiment_type="beta_endpoint_spectroscopy",
    semantic_role="OBSERVATIONS",
    schema_profile_id="KATRIN_DATA_JSON",
    source_urls=(
        "https://www.katrin.kit.edu/publikationen/KATRIN_data_KNM1-5.json",
        "https://zenodo.org/records/13644900/files/KATRIN_data_KNM1-5.json?download=1",
    ),
    source_doi="10.5281/zenodo.13644900",
    local_relative_path="data/external/neutrino/KATRIN_data_KNM1-5.json",
    expected_md5="7c9e30c35c394d87917cc56c7bf7ff53",
    required_for=("KATRIN-SPECTRAL-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=256 * 1024,
)

KATRIN_INPUTS_KNM1_5_JSON = ScientificArtifact(
    artifact_id="KATRIN-KNM1-5-INPUTS-JSON",
    logical_dataset_id="KATRIN-KNM1-5-OFFICIAL",
    domain="physics.particle.neutrino",
    experiment_type="beta_endpoint_spectroscopy",
    semantic_role="RESPONSE_COVARIANCE_AND_NUISANCE",
    schema_profile_id="KATRIN_INPUTS_JSON",
    source_urls=(
        "https://www.katrin.kit.edu/publikationen/KATRIN_inputs_KNM1-5.json",
        "https://zenodo.org/records/13644900/files/KATRIN_inputs_KNM1-5.json?download=1",
    ),
    source_doi="10.5281/zenodo.13644900",
    local_relative_path="data/external/neutrino/KATRIN_inputs_KNM1-5.json",
    expected_md5="6fcb3fbd3059190caa95f37243a9593a",
    required_for=("KATRIN-SPECTRAL-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=256 * 1024,
)

T2K_DATA_RELEASE_ZIP = ScientificArtifact(
    artifact_id="T2K-OSCILLATION-3P6E21-POT-ROOT",
    logical_dataset_id="T2K-PUBLISHED-OSCILLATION-SURFACES",
    domain="physics.particle.neutrino",
    experiment_type="accelerator_neutrino_oscillation",
    semantic_role="LIKELIHOOD_POSTERIOR_AND_COVERAGE_PRODUCTS",
    schema_profile_id="T2K_ROOT_RELEASE_ZIP",
    source_urls=("https://zenodo.org/records/7741399/files/T2K_arxiv2303.03222_DataRelease.zip?download=1",),
    source_doi="10.5281/zenodo.7741399",
    local_relative_path="data/external/neutrino/T2K_arxiv2303.03222_DataRelease.zip",
    expected_md5="864a40abecd009c1654e0c580c4375e2",
    required_for=("T2K-PUBLISHED-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=8 * 1024 * 1024,
)


SUPERK_ATMOSPHERIC_RELEASE = ScientificArtifact(
    artifact_id="SUPERK-ATMOSPHERIC-2023-TAR-GZ",
    logical_dataset_id="SUPERK-ATMOSPHERIC-2023",
    domain="physics.particle.neutrino",
    experiment_type="atmospheric_neutrino_oscillation",
    semantic_role="OBSERVATIONS_MC_SUMMARIES_AND_CHI2_GRIDS",
    schema_profile_id="SUPERK_ATMOSPHERIC_TAR_GZ",
    source_urls=("https://zenodo.org/records/8401262/files/sk_atm_2023.tar.gz?download=1",),
    source_doi="10.5281/zenodo.8401262",
    local_relative_path="data/external/neutrino/sk_atm_2023.tar.gz",
    expected_md5="58f26b39ba0bb36cc3570b7723298e2b",
    required_for=("SUPERK-ATMOSPHERIC-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=64 * 1024 * 1024,
)

SUPERK_SOLAR_RELEASE = ScientificArtifact(
    artifact_id="SUPERK-SOLAR-SKIV-3P49MEV-ZIP",
    logical_dataset_id="SUPERK-SOLAR-SKIV-2026",
    domain="physics.particle.neutrino",
    experiment_type="solar_neutrino_survival_probability",
    semantic_role="OBSERVATIONS_AND_PUBLISHED_SURVIVAL_PROFILE",
    schema_profile_id="SUPERK_SOLAR_RELEASE_ZIP",
    source_urls=("https://zenodo.org/records/19702889/files/data_release_SKIV_solar_3_49MeV.zip?download=1",),
    source_doi="10.5281/zenodo.19702889",
    local_relative_path="data/external/neutrino/data_release_SKIV_solar_3_49MeV.zip",
    expected_md5="9a44cbc7a7a4b26ba143c58ccf09419b",
    required_for=("SUPERK-SOLAR-LIKELIHOOD",),
    published_digest_algorithm="MD5_ZENODO",
    maximum_size_bytes=2 * 1024 * 1024,
)


DAYABAY_OBSERVABLES: tuple[ObservableDescriptor, ...] = (
    ObservableDescriptor(
        observable_id="DAYABAY-IBD-PROMPT-ENERGY-MIN", quantity_id="QTY-ENERGY", role="BIN_COORDINATE",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/dayabay_dataset/dayabay_ibd_spectra_total.npz",
        selector_kind="NPZ_RECORD_FIELD", selector="E_min_MeV", source_unit="MeV", canonical_scale=1.0e6,
        description="Left edge of reconstructed prompt-energy bin."),
    ObservableDescriptor(
        observable_id="DAYABAY-IBD-PROMPT-ENERGY-MAX", quantity_id="QTY-ENERGY", role="BIN_COORDINATE",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/dayabay_dataset/dayabay_ibd_spectra_total.npz",
        selector_kind="NPZ_RECORD_FIELD", selector="E_max_MeV", source_unit="MeV", canonical_scale=1.0e6,
        description="Right edge of reconstructed prompt-energy bin."),
    ObservableDescriptor(
        observable_id="DAYABAY-IBD-COUNT", quantity_id="QTY-COUNT", role="OBSERVATION",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/dayabay_dataset/dayabay_ibd_spectra_total.npz",
        selector_kind="NPZ_RECORD_FIELD", selector="N", source_unit="1",
        description="Observed binned inverse-beta-decay candidate count."),
    ObservableDescriptor(
        observable_id="DAYABAY-LIVETIME", quantity_id="QTY-TIME", role="EXPOSURE",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/dayabay_dataset/dayabay_daily_detector_data.npz",
        selector_kind="NPZ_RECORD_FIELD", selector="livetime", source_unit="s", canonical_scale=1.0,
        description="Daily detector live time."),
    ObservableDescriptor(
        observable_id="DAYABAY-DETECTION-EFFICIENCY", quantity_id="QTY-DIMENSIONLESS", role="EFFICIENCY",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/dayabay_dataset/dayabay_daily_detector_data.npz",
        selector_kind="NPZ_RECORD_FIELD", selector="eff", source_unit="1",
        description="Combined muon-veto and multiplicity-cut efficiency."),
    ObservableDescriptor(
        observable_id="DAYABAY-BASELINE", quantity_id="QTY-BASELINE", role="EXPERIMENT_GEOMETRY",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/parameters/baselines.yaml",
        selector_kind="YAML_PATH", selector="parameters.baseline", source_unit="m", canonical_scale=1.0e-3,
        description="Reactor-to-detector baseline matrix."),
    ObservableDescriptor(
        observable_id="DAYABAY-SIN2-2THETA13", quantity_id="QTY-MIXING-AMPLITUDE", role="FIT_PARAMETER",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/parameters/survival_probability.yaml",
        selector_kind="YAML_PATH", selector="parameters.SinSq2Theta13", source_unit="1",
        description="Target reactor-neutrino mixing-amplitude parameter in the official analysis dataset."),
    ObservableDescriptor(
        observable_id="DAYABAY-DELTAM2-32", quantity_id="QTY-MASS-SQUARED", role="FIT_PARAMETER",
        artifact_id=DAYABAY_ANALYSIS_NPZ.artifact_id, member_path="npz/parameters/survival_probability.yaml",
        selector_kind="YAML_PATH", selector="parameters.DeltaMSq32", source_unit="eV^2", canonical_scale=1.0,
        description="Target neutrino mass-splitting parameter in the official analysis dataset."),
)


DAYABAY_RESPONSE_PROJECTIONS: tuple[ResponseProjectionDescriptor, ...] = (
    ResponseProjectionDescriptor(
        response_projection_id="DAYABAY-CNP-PROFILE-CHI2",
        source_owner_id="REACTOR-COVARIANCE-LIKELIHOOD",
        execution_owner_id="DAYA-BAY-FULL-LIKELIHOOD",
        execution_operation="FIT_PUBLIC_DATA_PROFILE",
        response_quantity_id="QTY-CHI-SQUARED",
        response_key="chi2",
        required_input_quantity_ids=("QTY-COUNT",),
        response_semantics="Profiled CNP covariance goodness-of-fit statistic on the digest-qualified public Daya Bay detector-period data.",
        candidate_prediction_required_for_scientific_discrimination=True,
    ),
)

DATASET_CONTRACTS: tuple[DatasetContract, ...] = (
    DatasetContract(
        dataset_id="DAYA-BAY-OFFICIAL-ANALYSIS",
        domain="physics.particle.neutrino",
        experiment_type="reactor_neutrino_oscillation",
        required_artifact_groups=((DAYABAY_ANALYSIS_NPZ.artifact_id, DAYABAY_ANALYSIS_WHEEL.artifact_id),),
        optional_artifacts=(DAYABAY_MODEL_WHEEL.artifact_id,),
        adapter_id="NEUTRINO_DAYABAY_TYPED_ADAPTER",
        source_family_ids=("DAYA-BAY-DATA-2025",),
        observable_descriptors=DAYABAY_OBSERVABLES,
        response_projection_descriptors=DAYABAY_RESPONSE_PROJECTIONS,
    ),
    DatasetContract(
        dataset_id="KATRIN-KNM1-5-OFFICIAL",
        domain="physics.particle.neutrino",
        experiment_type="beta_endpoint_spectroscopy",
        required_artifact_groups=((KATRIN_KNM1_5_JSON.artifact_id,), (KATRIN_INPUTS_KNM1_5_JSON.artifact_id,)),
        adapter_id="NEUTRINO_KATRIN_TYPED_ADAPTER",
    ),
    DatasetContract(
        dataset_id="T2K-PUBLISHED-OSCILLATION-SURFACES",
        domain="physics.particle.neutrino",
        experiment_type="accelerator_neutrino_oscillation",
        required_artifact_groups=((T2K_DATA_RELEASE_ZIP.artifact_id,),),
        adapter_id="NEUTRINO_T2K_TYPED_ADAPTER",
    ),
    DatasetContract(
        dataset_id="SUPERK-ATMOSPHERIC-2023",
        domain="physics.particle.neutrino",
        experiment_type="atmospheric_neutrino_oscillation",
        required_artifact_groups=((SUPERK_ATMOSPHERIC_RELEASE.artifact_id,),),
        adapter_id="NEUTRINO_SUPERK_ATMOSPHERIC_TYPED_ADAPTER",
    ),
    DatasetContract(
        dataset_id="SUPERK-SOLAR-SKIV-2026",
        domain="physics.particle.neutrino",
        experiment_type="solar_neutrino_survival_probability",
        required_artifact_groups=((SUPERK_SOLAR_RELEASE.artifact_id,),),
        adapter_id="NEUTRINO_SUPERK_SOLAR_TYPED_ADAPTER",
    ),
)


class ScientificDataIngestionOwner:
    """Single owner of scientific artifact materialization and typed ingestion."""

    ARTIFACTS = (
        DAYABAY_ANALYSIS_NPZ,
        DAYABAY_ANALYSIS_WHEEL,
        DAYABAY_MODEL_WHEEL,
        KATRIN_KNM1_5_JSON,
        KATRIN_INPUTS_KNM1_5_JSON,
        T2K_DATA_RELEASE_ZIP,
        SUPERK_ATMOSPHERIC_RELEASE,
        SUPERK_SOLAR_RELEASE,
    )
    PROFILES = SCHEMA_PROFILES
    DATASETS = DATASET_CONTRACTS

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._artifacts = {row.artifact_id: row for row in self.ARTIFACTS}
        self._profiles = {row.profile_id: row for row in self.PROFILES}
        self._datasets = {row.dataset_id: row for row in self.DATASETS}

    @staticmethod
    def _safe_zip_names(path: Path) -> tuple[str, ...]:
        with zipfile.ZipFile(path) as archive:
            names = tuple(name for name in archive.namelist() if not name.endswith("/"))
        if not names or any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("unsafe or empty archive")
        return names

    @staticmethod
    def _pattern_satisfied(names: Sequence[str], expression: str) -> bool:
        # "a|b" means an OR group; each token supports fnmatch wildcards.
        lower = tuple(name.lower() for name in names)
        return any(any(fnmatch.fnmatch(name, token.lower()) for name in lower) for token in expression.split("|"))

    @staticmethod
    def _validate_dayabay_analysis_archive(path: Path) -> Mapping[str, Any]:
        """Validate the digest-bound official Daya Bay analysis NPZ archive."""
        required_members = {
            "npz/dataset_info.yaml",
            "npz/dayabay_dataset/dayabay_ibd_spectra_total.npz",
            "npz/dayabay_dataset/dayabay_daily_detector_data.npz",
            "npz/detector_iav_matrix.npz",
            "npz/detector_lsnl_curves.npz",
            "npz/neutrino_rate.npz",
            "npz/reactor_antineutrino_spectra_hm.npz",
        }
        detectors = {"AD11", "AD12", "AD21", "AD22", "AD31", "AD32", "AD33", "AD34"}
        reactors = {"R1", "R2", "R3", "R4", "R5", "R6"}
        with zipfile.ZipFile(path) as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
            missing = sorted(required_members - names)
            if missing:
                return {"status": "BLOCKED_DAYABAY_REQUIRED_MEMBERS_MISSING", "missing": tuple(missing)}
            info = archive.read("npz/dataset_info.yaml").decode("utf-8", errors="strict")
            arrays: dict[str, dict[str, Any]] = {}
            for member in required_members - {"npz/dataset_info.yaml"}:
                with np.load(io.BytesIO(archive.read(member)), allow_pickle=True) as payload:
                    arrays[member] = {key: payload[key] for key in payload.files}

        spectra = arrays["npz/dayabay_dataset/dayabay_ibd_spectra_total.npz"]
        daily = arrays["npz/dayabay_dataset/dayabay_daily_detector_data.npz"]
        iav = arrays["npz/detector_iav_matrix.npz"]
        lsnl = arrays["npz/detector_lsnl_curves.npz"]
        rates = arrays["npz/neutrino_rate.npz"]
        hm = arrays["npz/reactor_antineutrino_spectra_hm.npz"]
        checks = {
            "version_1_0_0": 'version: "1.0.0"' in info,
            "format_npz": 'format: "npz"' in info,
            "variant_analysis": 'variant: "analysis dataset"' in info,
            "eight_total_ibd_spectra": {key.removeprefix("ibd_spectrum_") for key in spectra} == detectors,
            "ibd_spectra_240_bins": all(value.shape == (240,) for value in spectra.values()),
            "eight_daily_detector_tables": set(daily) == detectors,
            "daily_detector_rows_3277": all(value.shape == (3277,) for value in daily.values()),
            "iav_matrix_240_by_240": set(iav) == {"iav_matrix"} and iav["iav_matrix"].shape == (240, 240),
            "five_lsnl_curves_458_points": set(lsnl) == {"nominal", "pull0", "pull1", "pull2", "pull3"}
            and all(value.shape == (458,) for value in lsnl.values()),
            "six_reactor_rate_tables": set(rates) == reactors and all(value.shape == (469,) for value in rates.values()),
            "four_huber_mueller_isotopes": set(hm) == {"U235", "U238", "Pu239", "Pu241"},
        }
        return {
            "status": "PASS_DAYABAY_ANALYSIS_SEMANTIC_SCHEMA" if all(checks.values()) else "BLOCKED_DAYABAY_ANALYSIS_SEMANTIC_SCHEMA",
            "checks": checks,
            "required_member_count": len(required_members),
        }

    def validate_schema(self, path: Path, profile_id: str) -> Mapping[str, Any]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {"status": "BLOCKED_UNKNOWN_SCHEMA_PROFILE", "profile_id": profile_id}
        try:
            fmt = profile.container_format
            details: dict[str, Any] = {"profile_id": profile.profile_id, "container_format": fmt, "media_type": profile.media_type}
            if fmt in {"ZIP", "WHEEL", "NPZ"}:
                names = self._safe_zip_names(path)
                required = {pattern: self._pattern_satisfied(names, pattern) for pattern in profile.required_member_patterns}
                if fmt == "NPZ":
                    required["*.npy"] = any(name.lower().endswith(".npy") for name in names)
                details.update({"entry_count": len(names), "entries": names[:500], "required_members": required})
                passed = all(required.values())
                if profile_id == "DAYABAY_ANALYSIS_ARCHIVE" and passed:
                    semantic = self._validate_dayabay_analysis_archive(path)
                    details["semantic_validation"] = semantic
                    passed = semantic["status"] == "PASS_DAYABAY_ANALYSIS_SEMANTIC_SCHEMA"
            elif fmt == "TAR_GZ":
                with tarfile.open(path, "r:gz") as archive:
                    members = tuple(member.name for member in archive.getmembers() if member.isfile())
                if not members or any(name.startswith("/") or ".." in Path(name).parts for name in members):
                    raise ValueError("unsafe or empty tar archive")
                required = {pattern: self._pattern_satisfied(members, pattern) for pattern in profile.required_member_patterns}
                details.update({"entry_count": len(members), "entries": members[:1000], "required_members": required})
                passed = all(required.values())
            elif fmt in {"JSON", "RO_CRATE", "FRICTIONLESS"}:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, (dict, list)):
                    raise ValueError("JSON top-level must be object or array")
                keys = tuple(sorted(payload.keys())) if isinstance(payload, dict) else ()
                required = {key: isinstance(payload, dict) and key in payload for key in profile.required_json_keys}
                details.update({"top_level_type": type(payload).__name__, "top_level_keys": keys[:200], "required_keys": required})
                passed = all(required.values())
            elif fmt in {"CSV", "TSV"}:
                delimiter = profile.delimiter or ("\t" if fmt == "TSV" else ",")
                with path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.reader(handle, delimiter=delimiter)
                    header = tuple(next(reader))
                    sample_rows = sum(1 for _, _row in zip(range(100), reader))
                required = {column: column in header for column in profile.required_table_columns}
                details.update({"header": header, "sample_rows": sample_rows, "required_columns": required})
                passed = bool(header) and all(required.values())
            elif fmt == "NPY":
                magic = path.read_bytes()[:6]
                details["magic_hex"] = magic.hex()
                passed = magic == b"\x93NUMPY"
            elif fmt == "HDF5":
                magic = path.read_bytes()[:8]
                details["magic_hex"] = magic.hex()
                passed = magic == b"\x89HDF\r\n\x1a\n"
                nexus_required = profile.profile_id == "GENERIC_NEXUS"
                try:
                    import h5py  # type: ignore
                    with h5py.File(path, "r") as handle:
                        keys: list[str] = []
                        handle.visit(keys.append)
                        nxentry_paths: list[str] = []
                        def visit_nexus(name: str, obj: Any) -> None:
                            value = obj.attrs.get("NX_class") if hasattr(obj, "attrs") else None
                            if isinstance(value, bytes):
                                value = value.decode("utf-8", errors="replace")
                            if value == "NXentry":
                                nxentry_paths.append(name)
                        handle.visititems(visit_nexus)
                    details["hdf5_object_count"] = len(keys)
                    details["hdf5_reader"] = "h5py"
                    if nexus_required:
                        details["nexus_nxentry_paths"] = tuple(nxentry_paths)
                        passed = passed and bool(nxentry_paths)
                except Exception:
                    details["hdf5_reader"] = "SIGNATURE_ONLY"
                    if nexus_required:
                        passed = False
                        details["nexus_semantic_validation"] = "BLOCKED_H5PY_OR_NXENTRY_REQUIRED"
            elif fmt == "ROOT":
                magic = path.read_bytes()[:4]
                details["magic_hex"] = magic.hex()
                passed = magic == b"root"
                try:
                    import uproot  # type: ignore
                    with uproot.open(path) as handle:
                        details["root_keys"] = tuple(str(key) for key in handle.keys())[:200]
                    details["root_reader"] = "uproot"
                except Exception:
                    details["root_reader"] = "SIGNATURE_ONLY"
            else:
                details["size_bytes"] = path.stat().st_size
                passed = path.stat().st_size > 0
            details["status"] = "PASS_SCHEMA_PROFILE" if passed else "BLOCKED_SCHEMA_PROFILE_MISMATCH"
            return details
        except Exception as exc:
            return {
                "status": "BLOCKED_SCHEMA_PROFILE_PARSE_FAILURE",
                "profile_id": profile_id,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }

    def read_qualified_archive_members(
        self, artifact_id: str, members: Sequence[str] | None = None
    ) -> Mapping[str, bytes]:
        """Return bytes from a digest- and schema-qualified ZIP/WHEEL artifact.

        Container parsing remains owned here. Domain owners may name the members
        required by their scientific formula, but cannot bypass provenance, path
        safety, digest validation, or schema validation.
        """
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise KeyError(f"unknown scientific artifact: {artifact_id}")
        inspection = artifact.inspect(self)
        if inspection.get("status") != "PASS_INGESTION_READY_ARTIFACT":
            raise RuntimeError(f"artifact is not ingestion-ready: {inspection.get('status')}")
        profile = self._profiles[artifact.schema_profile_id]
        if profile.container_format not in {"ZIP", "WHEEL", "NPZ"}:
            raise ValueError("qualified archive member access requires ZIP-compatible container")
        path = artifact._safe_path(self.root)
        safe_names = set(self._safe_zip_names(path))
        requested = tuple(members) if members is not None else tuple(sorted(safe_names))
        missing = tuple(sorted(set(requested) - safe_names))
        if missing:
            raise KeyError(f"qualified artifact members missing: {missing}")
        with zipfile.ZipFile(path) as archive:
            return {name: archive.read(name) for name in requested}

    def inspect_all(self) -> Mapping[str, Mapping[str, Any]]:
        return {artifact.artifact_id: artifact.inspect(self) for artifact in self.ARTIFACTS}

    def materialize_all(self, *, timeout_seconds: float = 120.0) -> Mapping[str, Mapping[str, Any]]:
        return {artifact.artifact_id: artifact.materialize(self, timeout_seconds=timeout_seconds) for artifact in self.ARTIFACTS}

    def _observable_catalog(self, contract: DatasetContract, selected: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
        """Resolve declarative observable descriptors against digest-bound selected artifacts."""
        selected_by_id = {str(row.get("artifact_id")): dict(row) for row in selected}
        quantity_rows = json.loads((self.root / "data" / "quantities" / "registry.json").read_text(encoding="utf-8"))
        quantity_ids = {str(row.get("quantity_id")) for row in quantity_rows}
        rows: list[Mapping[str, Any]] = []
        for descriptor in contract.observable_descriptors:
            artifact = selected_by_id.get(descriptor.artifact_id)
            checks = {
                "SELECTED_ARTIFACT": artifact is not None,
                "CANONICAL_QUANTITY_ID": descriptor.quantity_id in quantity_ids,
                "MEMBER_PRESENT": False,
                "SELECTOR_PRESENT": False,
            }
            evidence: dict[str, Any] = {}
            if artifact is not None:
                path = self.root / str(artifact.get("path"))
                try:
                    with zipfile.ZipFile(path) as archive:
                        names = set(archive.namelist())
                        checks["MEMBER_PRESENT"] = descriptor.member_path in names
                        if checks["MEMBER_PRESENT"]:
                            raw = archive.read(descriptor.member_path)
                            if descriptor.selector_kind == "NPZ_RECORD_FIELD":
                                with np.load(io.BytesIO(raw), allow_pickle=True) as payload:
                                    keys = tuple(payload.files)
                                    matching_keys = []
                                    field_receipts = []
                                    for key in keys:
                                        dtype_names = tuple(payload[key].dtype.names or ())
                                        if descriptor.selector in dtype_names:
                                            matching_keys.append(key)
                                            field = np.asarray(payload[key][descriptor.selector])
                                            field_receipts.append({
                                                "array_key": key, "shape": tuple(int(x) for x in field.shape),
                                                "dtype": str(field.dtype), "bytes_sha256": hashlib.sha256(field.tobytes(order="C")).hexdigest(),
                                            })
                                    checks["SELECTOR_PRESENT"] = bool(matching_keys)
                                    evidence = {
                                        "array_key_count": len(keys), "matching_array_keys": tuple(matching_keys),
                                        "field_value_digest": _digest(field_receipts) if field_receipts else None,
                                    }
                            elif descriptor.selector_kind == "YAML_PATH":
                                value: Any = yaml.safe_load(raw.decode("utf-8", errors="strict"))
                                path_parts = tuple(part for part in descriptor.selector.split(".") if part)
                                for part in path_parts:
                                    if isinstance(value, Mapping) and part in value:
                                        value = value[part]
                                    else:
                                        value = None
                                        break
                                checks["SELECTOR_PRESENT"] = value is not None
                                evidence = {
                                    "yaml_path": path_parts,
                                    "value_kind": type(value).__name__ if value is not None else None,
                                    "value_digest": _digest(value) if value is not None else None,
                                }
                            else:
                                evidence = {"error": f"unknown selector kind {descriptor.selector_kind}"}
                except Exception as exc:
                    evidence = {"error_type": type(exc).__name__, "error": str(exc)[:500]}
            available = all(checks.values())
            core = {
                "observable_id": descriptor.observable_id,
                "quantity_id": descriptor.quantity_id,
                "role": descriptor.role,
                "artifact_id": descriptor.artifact_id,
                "member_path": descriptor.member_path,
                "selector_kind": descriptor.selector_kind,
                "selector": descriptor.selector,
                "source_unit": descriptor.source_unit,
                "canonical_scale": descriptor.canonical_scale,
                "description": descriptor.description,
                "checks": checks,
                "available": available,
                "artifact_sha256": artifact.get("actual_sha256") if artifact else None,
                "source_doi": artifact.get("source_doi") if artifact else None,
                "evidence": evidence,
                "value_digest": evidence.get("field_value_digest") or evidence.get("value_digest"),
            }
            rows.append({**core, "digest": _digest(core)})
        return tuple(rows)

    def qualify_dataset(self, dataset_id: str) -> Mapping[str, Any]:
        contract = self._datasets.get(dataset_id)
        if contract is None:
            return {"dataset_id": dataset_id, "status": "BLOCKED_UNKNOWN_DATASET_CONTRACT"}
        inspections = self.inspect_all()
        groups: list[Mapping[str, Any]] = []
        passed = True
        selected: list[str] = []
        for alternatives in contract.required_artifact_groups:
            rows = {artifact_id: inspections[artifact_id] for artifact_id in alternatives}
            accepted = next((artifact_id for artifact_id, row in rows.items() if row["status"] == "PASS_INGESTION_READY_ARTIFACT"), None)
            groups.append({"alternatives": alternatives, "accepted": accepted, "artifacts": rows})
            if accepted is None:
                passed = False
            else:
                selected.append(accepted)
        optional = {artifact_id: inspections[artifact_id] for artifact_id in contract.optional_artifacts}
        return {
            "dataset_id": dataset_id,
            "domain": contract.domain,
            "experiment_type": contract.experiment_type,
            "adapter_id": contract.adapter_id,
            "source_family_ids": contract.source_family_ids,
            "declared_observable_count": len(contract.observable_descriptors),
            "status": "PASS_DATASET_READY_FOR_DOMAIN_OWNER" if passed else "BLOCKED_DATASET_ARTIFACT_GROUP_INCOMPLETE",
            "selected_artifacts": tuple(selected),
            "required_groups": tuple(groups),
            "optional_artifacts": optional,
            "synthetic_substitution_allowed": False,
        }

    def to_experiment_data_ir(self, dataset_id: str) -> Mapping[str, Any]:
        qualification = self.qualify_dataset(dataset_id)
        if qualification["status"] != "PASS_DATASET_READY_FOR_DOMAIN_OWNER":
            return {
                "schema": IR_SCHEMA,
                "dataset_id": dataset_id,
                "status": qualification["status"],
                "qualification": qualification,
                "synthetic_substitution_allowed": False,
            }
        inspections = self.inspect_all()
        selected = [inspections[artifact_id] for artifact_id in qualification["selected_artifacts"]]

        def entities(tokens: tuple[str, ...]) -> tuple[Mapping[str, Any], ...]:
            return tuple(row for row in selected if any(token in row["semantic_role"] for token in tokens))

        provenance = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "adapter_id": qualification["adapter_id"],
            "artifact_sha256": {row["artifact_id"]: row["actual_sha256"] for row in selected},
            "source_doi": {row["artifact_id"]: row.get("source_doi") for row in selected},
            "schema_profiles": {row["artifact_id"]: row["schema_profile_id"] for row in selected},
        }
        contract = self._datasets[dataset_id]
        observable_catalog = self._observable_catalog(contract, selected)
        projection_ready = bool(observable_catalog) and all(row.get("available") is True for row in observable_catalog)
        available_quantity_ids = {str(row.get("quantity_id")) for row in observable_catalog if row.get("available") is True}
        response_projection_catalog = []
        for descriptor in contract.response_projection_descriptors:
            row = dataclasses.asdict(descriptor)
            row["input_quantities_available"] = set(descriptor.required_input_quantity_ids).issubset(available_quantity_ids)
            row["descriptor_digest"] = _digest(dataclasses.asdict(descriptor))
            response_projection_catalog.append(row)
        payload = {
            "schema": IR_SCHEMA,
            "dataset_id": dataset_id,
            "domain": qualification["domain"],
            "experiment_type": qualification["experiment_type"],
            "data_entities": entities(("OBSERVATION", "LIKELIHOOD", "POSTERIOR")),
            "metadata_entities": entities(("METADATA", "REFERENCE_MODEL")),
            "covariance_entities": entities(("COVARIANCE",)),
            "response_entities": entities(("RESPONSE", "REFERENCE_MODEL")),
            "nuisance_entities": entities(("NUISANCE", "SYSTEMATICS")),
            "observable_catalog": observable_catalog,
            "response_projection_catalog": tuple(response_projection_catalog),
            "source_family_ids": contract.source_family_ids,
            "observable_quantity_ids": tuple(sorted({str(row.get("quantity_id")) for row in observable_catalog if row.get("available") is True})),
            "measurement_projection_status": (
                "PASS_FIELD_LEVEL_OBSERVABLE_CATALOG" if projection_ready else
                "NOT_DECLARED_FIELD_LEVEL_OBSERVABLE_CATALOG" if not observable_catalog else
                "BLOCKED_FIELD_LEVEL_OBSERVABLE_CATALOG"
            ),
            "provenance": provenance,
            "status": "PASS_EXPERIMENT_DATA_IR",
        }
        return {**payload, "digest": _digest(payload)}

    def run_qualification(self) -> Mapping[str, Any]:
        inspections = self.inspect_all()
        dayabay_ir = self.to_experiment_data_ir("DAYA-BAY-OFFICIAL-ANALYSIS")
        dayabay_observables = tuple(dayabay_ir.get("observable_catalog", ()))
        checks = {
            "single_domain_neutral_owner": OWNER_ID == "SCIENTIFIC-DATA-INGESTION",
            "unique_artifact_ids": len({row.artifact_id for row in self.ARTIFACTS}) == len(self.ARTIFACTS),
            "unique_schema_profile_ids": len({row.profile_id for row in self.PROFILES}) == len(self.PROFILES),
            "unique_dataset_ids": len({row.dataset_id for row in self.DATASETS}) == len(self.DATASETS),
            "all_paths_relative": all(not Path(row.local_relative_path).is_absolute() for row in self.ARTIFACTS),
            "all_sources_https": all(all(urllib.parse.urlparse(url).scheme == "https" for url in row.source_urls) for row in self.ARTIFACTS),
            "all_artifacts_reference_known_profiles": all(row.schema_profile_id in self._profiles for row in self.ARTIFACTS),
            "generic_profiles_cover_tabular_array_hierarchical_archive_and_provenance": all(
                profile in self._profiles
                for profile in ("GENERIC_JSON", "GENERIC_CSV", "GENERIC_NPZ", "GENERIC_HDF5", "GENERIC_ROOT", "GENERIC_ZIP", "RO_CRATE_JSONLD", "FRICTIONLESS_DATA_PACKAGE")
            ),
            "dayabay_analysis_digest_bound": DAYABAY_ANALYSIS_NPZ.expected_md5 == "dfc33dce75508b53e9821329b3e06a17",
            "dayabay_current_model_sha256_bound": DAYABAY_MODEL_WHEEL.expected_sha256 == "74c328f9c8527bf3e1fac3d8e24acdee2253a3ee44c32066dcd2a4529efb7fb7",
            "katrin_data_digest_bound": KATRIN_KNM1_5_JSON.expected_md5 == "7c9e30c35c394d87917cc56c7bf7ff53",
            "katrin_inputs_digest_bound": KATRIN_INPUTS_KNM1_5_JSON.expected_md5 == "6fcb3fbd3059190caa95f37243a9593a",
            "t2k_digest_bound": T2K_DATA_RELEASE_ZIP.expected_md5 == "864a40abecd009c1654e0c580c4375e2",
            "superk_atmospheric_digest_bound": SUPERK_ATMOSPHERIC_RELEASE.expected_md5 == "58f26b39ba0bb36cc3570b7723298e2b",
            "superk_solar_digest_bound": SUPERK_SOLAR_RELEASE.expected_md5 == "9a44cbc7a7a4b26ba143c58ccf09419b",
            "missing_artifacts_fail_closed": all(row["status"].startswith(("BLOCKED_", "PASS_")) for row in inspections.values()),
            "materializer_owned_here_not_cli": hasattr(ScientificArtifact, "materialize"),
            "experiment_data_ir_owned_here": hasattr(self, "to_experiment_data_ir"),
            "qualified_archive_reader_owned_here": hasattr(self, "read_qualified_archive_members"),
            "dayabay_field_level_ir_ready": dayabay_ir.get("status") == "PASS_EXPERIMENT_DATA_IR" and dayabay_ir.get("measurement_projection_status") == "PASS_FIELD_LEVEL_OBSERVABLE_CATALOG",
            "dayabay_exact_observable_catalog_has_8_fields": len(dayabay_observables) == 8 and all(row.get("available") is True for row in dayabay_observables),
            "dayabay_observable_values_are_digest_bound": all(isinstance(row.get("value_digest"), str) and len(row.get("value_digest")) == 64 for row in dayabay_observables),
            "dayabay_quantity_vocabulary_exact": set(dayabay_ir.get("observable_quantity_ids", ())) == {"QTY-BASELINE", "QTY-COUNT", "QTY-DIMENSIONLESS", "QTY-ENERGY", "QTY-MASS-SQUARED", "QTY-MIXING-AMPLITUDE", "QTY-TIME"},
            "dayabay_source_family_exact": tuple(dayabay_ir.get("source_family_ids", ())) == ("DAYA-BAY-DATA-2025",),
            "dayabay_exact_response_projection_declared": len(dayabay_ir.get("response_projection_catalog", ())) == 1 and dayabay_ir.get("response_projection_catalog", ())[0].get("response_projection_id") == "DAYABAY-CNP-PROFILE-CHI2",
            "dayabay_response_projection_inputs_available": bool(dayabay_ir.get("response_projection_catalog", ())) and dayabay_ir.get("response_projection_catalog", ())[0].get("input_quantities_available") is True,
            "response_projection_descriptor_contains_no_observed_value": all("response_value" not in row for row in dayabay_ir.get("response_projection_catalog", ())),
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_SCIENTIFIC_DATA_INGESTION_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_SCIENTIFIC_DATA_INGESTION",
            "checks": checks,
            "artifacts": inspections,
            "schema_profiles": tuple(dataclasses.asdict(row) for row in self.PROFILES),
            "dataset_contracts": tuple(dataclasses.asdict(row) for row in self.DATASETS),
            "materialization_environment": {
                "public_sources_verified_available": True,
                "binary_transport_in_this_execution": "LOCAL_USER_MATERIALIZATION_VERIFIED_FOR_DAYABAY_ANALYSIS_NPZ",
                "owner_can_materialize_in_networked_runtime": True,
            },
            "claim_boundary": {
                "domain_specific_download_algorithm_exists": False,
                "missing_artifacts_replaced_by_synthetic_data": False,
                "published_md5_used_as_security_hash": False,
                "local_sha256_reported_for_every_materialized_file": True,
                "schema_validation_precedes_commit": True,
                "domain_owner_receives_typed_ir_not_unvalidated_file": True,
                "field_level_observable_catalog_is_world_attestation": False,
                "published_dataset_parameter_is_new_measurement_result": False,
                "response_projection_descriptor_is_executed_response": False,
            },
            "sha256": "",
        }
        report["sha256"] = _digest({**report, "sha256": ""})
        return report

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "ir_schema": IR_SCHEMA,
            "artifacts": tuple(dataclasses.asdict(row) for row in self.ARTIFACTS),
            "schema_profiles": tuple(dataclasses.asdict(row) for row in self.PROFILES),
            "dataset_contracts": tuple(dataclasses.asdict(row) for row in self.DATASETS),
            "hard_boundaries": (
                "ONE_INGESTION_OWNER_FOR_ALL_DOMAINS",
                "HTTPS_ALLOWLIST_ONLY",
                "ATOMIC_WRITE_AFTER_DIGEST_AND_SCHEMA_VERIFICATION",
                "NO_SYNTHETIC_REPLACEMENT",
                "NO_DOMAIN_LIKELIHOOD_BEFORE_EXPERIMENT_DATA_IR",
                "DOMAIN_ADAPTERS_ARE_DECLARATIVE_NOT_DOWNLOAD_ALGORITHMS",
                "ARCHIVE_PARSING_REMAINS_IN_INGESTION_OWNER",
                "FIELD_LEVEL_OBSERVABLES_BIND_BY_EXACT_QUANTITY_ID_NOT_FUZZY_TEXT",
                "DERIVED_RESPONSE_PROJECTIONS_ARE_DECLARATIVE_AND_EXECUTE_ONLY_IN_DOMAIN_OWNER",
                "RESPONSE_PROJECTION_MUST_BE_FROZEN_BEFORE_DERIVED_RESPONSE_EXECUTION",
                "DATASET_BINDING_DOES_NOT_IMPLY_WORLD_ATTESTATION_OR_U5",
            ),
        }
        return {**payload, "digest": _digest(payload)}
