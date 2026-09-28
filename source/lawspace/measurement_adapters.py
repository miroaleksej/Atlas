"""Small explicit adapters; scientific selection and adjudication live elsewhere."""
from __future__ import annotations

import json
from pathlib import Path


class LocalEvidenceArchive:
    """Replay existing bytes, never describe a local copy as a new acquisition."""
    adapter_id = "LOCAL-EVIDENCE-ARCHIVE/1"
    source_class = "OBSERVATIONAL_ARCHIVE"

    def __init__(self, root, source_id):
        self.root = Path(root).resolve()
        self.source_id = source_id
        # Expected content hashes bind the bytes. Keeping machine-local paths
        # out of the public binding makes qualification receipts reproducible.
        self.configuration = {"archive_identity": source_id}

    def _path(self, request):
        path = (self.root / request["path"]).resolve()
        if self.root not in path.parents:
            raise ValueError("archive path escapes declared root")
        return path

    def preflight(self, contract):
        if contract["evidence_mode"] == "PROSPECTIVE_REQUEST":
            raise ValueError("existing local archive requires retrospective evidence mode")
        for sample in contract["samples"]:
            self._path(sample["request"])
            if not sample.get("expected_sha256"):
                raise ValueError("local replay requires frozen SHA-256")
        return []

    def acquire(self, request, *, idempotency_key=None):
        return self._path(request).read_bytes()


class TabularJSONMeasurement:
    """Typed column projection, not fitting; useful for any tabular domain.

    Cases declare observation_column and feature_columns, plus explicit unit
    labels. Unit conversion belongs in a different, explicitly bound adapter.
    """
    adapter_id = "TABULAR-JSON-MEASUREMENT/1"

    def preflight(self, contract):
        for case in contract["cases"]:
            features = case["feature_columns"]
            required = {f for form in contract["forms"] if form["case_id"] == case["case_id"] for f in form["feature_ids"]}
            if not required <= set(features):
                raise ValueError("missing feature column mapping")
            if case["observation_column"] in features.values():
                raise ValueError("observed target cannot be a predictor")
            columns = {case["observation_column"], *features.values()}
            if any(not case["units"].get(x) for x in columns):
                raise ValueError("explicit column units required")
        return []

    def measure(self, evidence, cases):
        data = json.loads(evidence)
        result = {}
        for case in cases:
            columns = {case["observation_column"], *case["feature_columns"].values()}
            if any(data["units"][x] != case["units"][x] for x in columns):
                raise ValueError("measurement unit mismatch")
            result[case["case_id"]] = {
                "observed": data["columns"][case["observation_column"]],
                "features": {key: data["columns"][column] for key, column in case["feature_columns"].items()}}
        return result
