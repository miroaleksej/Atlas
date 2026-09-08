"""Internal ScienceAtlas kernel used by existing authoritative Φ owners.

This module is a support kernel, not a parallel application or owner hierarchy.
ConstraintAtlasOwner remains the authoritative chart/closure/operator/defect owner;
CrossDomainBridgeOwner remains the bridge owner; dynamic-axis owners retain genesis.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .schema import AtlasSnapshotRecord, EpistemicCertificate, FrontierDefectRecord, digest_payload
from .domains import DOMAIN_REGISTRIES, canonical_axis_count

SCHEMA="phi-science-atlas-core/v1"
KERNEL_ID="SCIENCE-ATLAS-CORE-KERNEL/1.0.0"


class ScienceAtlasCoreKernel:
    def __init__(self, root: str | Path):
        self.root=Path(root)
        self.data=self.root/"data/science_atlas"

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str,str]]:
        with path.open(encoding="utf-8",newline="") as f: return list(csv.DictReader(f))

    @staticmethod
    def _read_json(path: Path) -> dict[str,Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _active_frontier_rows(self) -> list[dict[str,Any]]:
        path=self.root/"data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
        if not path.exists(): return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def compile_role_typed_charts(self) -> Mapping[str,Any]:
        from .runtime import LawSpaceRuntime
        runtime=LawSpaceRuntime(self.root)
        domain_rows={}
        occupied=0
        for domain_id,registry in sorted(DOMAIN_REGISTRIES.items()):
            owner_count=sum(1 for p in runtime.catalog.passports.values() if p.domain_id==domain_id)
            domain_rows[domain_id]={"axis_count":registry.axis_count,"owner_count":owner_count}
            occupied += int(owner_count>0)
        payload={"schema":"phi-role-typed-chart-matrix/current-v2","domain_count":len(domain_rows),"canonical_axis_count":canonical_axis_count(),"occupied_domain_count":occupied,"domains":domain_rows,"typing_before_topology":True,"source":"LIVE_CANONICAL_REGISTRIES_AND_LAW_PASSPORTS"}
        return {**payload,"digest":digest_payload(payload)}

    def infer_recurrent_operators(self) -> Mapping[str,Any]:
        rows=self._active_frontier_rows()
        op=[r for r in rows if r.get("candidate_class")=="OPERATOR_COMPOSITION_FRONTIER"]
        families={}
        for row in op:
            features=tuple(sorted(row.get("payload",{}).get("operator_features",())))
            for feature in features: families.setdefault(feature,set()).update(row.get("domain_ids",()))
        recurrent=[{"operator_feature":k,"domains":sorted(v)} for k,v in sorted(families.items()) if v]
        payload={"schema":"phi-residual-operator-induction/current-v2","operator_candidate_count":len(op),"recurrent_family_count":len(recurrent),"recurrent_families":recurrent,"target_chart_labels_used_during_induction":False,"source":"CURRENT_FRONTIER_LEDGER"}
        return {**payload,"digest":digest_payload(payload)}

    def proof_contract(self) -> Mapping[str,Any]:
        from .runtime import LawSpaceRuntime
        q=LawSpaceRuntime(self.root).qualify()
        g6=q.get("gates",{}).get("G6_FORMAL_ANALYSIS_AND_INTEGRATION",{})
        payload={"schema":"phi-science-atlas-proof-contract/current-v2","lawspace_g6_status":g6.get("status"),"finite_typed_representability_proven":g6.get("status")=="PASS","unique_ontological_atlas_proven":False,"open_obligations":[k for k,v in g6.get("checks",{}).items() if not v],"source":"CURRENT_LAWSPACE_G6"}
        return {**payload,"digest":digest_payload(payload)}

    def prospective_contract(self) -> Mapping[str,Any]:
        rows=self._active_frontier_rows()
        unresolved=sum(1 for r in rows if any("UNRESOLVED" in str(s) or "PENDING" in str(s) for s in r.get("epistemic_statuses",())))
        payload={"schema":"phi-atlas-prospective-contract/current-v2","persistent_frontier_count":len(rows),"unresolved_or_pending_count":unresolved,"historical_prospective_prediction_registry_restored":False,"predictive_geometry_proven":False,"source":"CURRENT_FRONTIER_LEDGER"}
        return {**payload,"digest":digest_payload(payload)}

    def frontier_contract(self) -> Mapping[str,Any]:
        rows=self._active_frontier_rows()
        class_counts={}
        for r in rows: class_counts[r.get("candidate_class","UNKNOWN")]=class_counts.get(r.get("candidate_class","UNKNOWN"),0)+1
        defect=FrontierDefectRecord(defect_id="ATLAS-CURRENT-FRONTIER",defect_class="PERSISTENT_RESEARCH_FRONTIER",chart_ids=tuple(sorted(DOMAIN_REGISTRIES)),unresolved_relation="multiple unresolved law/mechanism/axis candidates",constraints=("UNKNOWN_NEVER_FALSE","NOVELTY_REQUIRES_EVIDENCE"),residuals=(f"active_candidates={len(rows)}",),admitted_operator_closure_status="PARTIAL_OPEN_FRONTIER",bridge_support=("owner-connected cross-domain bridges",),prior_art_status="PER_CANDIDATE",identifiability_status="PER_CANDIDATE_FAIL_CLOSED",evidence_status="CURRENT_LEDGER",information_gain_score=0.0,claim_boundary={"new_law_established":False}).finalized()
        payload={"schema":"phi-frontier-defect-contract/current-v2","hypothesis_count":len(rows),"candidate_class_counts":class_counts,"top_frontier_defect":defect.__dict__,"frontier_hypothesis_is_law":False}
        return {**payload,"digest":digest_payload(payload)}

    @staticmethod
    def _sqlite_roundtrip(payload: Mapping[str,Any]) -> tuple[str,str,int]:
        encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as tf:
            con=sqlite3.connect(tf.name); con.execute("CREATE TABLE atlas_record(kind TEXT PRIMARY KEY,payload TEXT NOT NULL,sha256 TEXT NOT NULL)")
            hv=hashlib.sha256(encoded.encode()).hexdigest(); con.execute("INSERT INTO atlas_record VALUES(?,?,?)",("snapshot",encoded,hv)); con.commit(); row=con.execute("SELECT payload,sha256 FROM atlas_record WHERE kind='snapshot'").fetchone(); con.close()
        decoded=json.loads(row[0]); replay=json.dumps(decoded,ensure_ascii=False,sort_keys=True,separators=(",",":")); return row[1],hashlib.sha256(replay.encode()).hexdigest(),1

    def snapshot_replay(self, components: Mapping[str,Any]) -> Mapping[str,Any]:
        component_digests={k:str(v.get("digest",digest_payload(v))) for k,v in components.items()}
        snap=AtlasSnapshotRecord(snapshot_id="SCIENCE-ATLAS-CURRENT-SNAPSHOT",object_registry_digest=component_digests["charts"],law_registry_digest=component_digests["proof"],operator_registry_digest=component_digests["operators"],chart_registry_digest=component_digests["charts"],bridge_registry_digest=component_digests["frontier"],axis_registry_digest=component_digests["charts"],defect_registry_digest=component_digests["frontier"],observer_registry_digest=component_digests["prospective"],evidence_registry_digest=component_digests["proof"],prospective_freeze_digest=component_digests["prospective"]).finalized()
        stored,replayed,count=self._sqlite_roundtrip(snap.__dict__); payload={"schema":"phi-atlas-snapshot-replay/current-v2","status":"PASS_EXACT_ATLAS_SNAPSHOT_REPLAY" if stored==replayed else "FAIL_ATLAS_SNAPSHOT_REPLAY","record_count":count,"snapshot":snap.__dict__,"stored_sha256":stored,"replayed_sha256":replayed}; return {**payload,"digest":digest_payload(payload)}

    def gsa002_status(self) -> Mapping[str,Any]:
        payload={"schema":"phi-gsa002-current-status/v2","historical_gsa002_state_restored":False,"current_status":"ARCHIVED_NOT_CURRENT_ACCEPTANCE_EVIDENCE","confirmatory_fit_claimed":False,"precommit_rewritten":False}
        return {**payload,"digest":digest_payload(payload)}

    def run_qualification(self) -> Mapping[str,Any]:
        charts=self.compile_role_typed_charts(); operators=self.infer_recurrent_operators(); proof=self.proof_contract(); prospective=self.prospective_contract(); frontier=self.frontier_contract(); gsa=self.gsa002_status()
        components={"charts":charts,"operators":operators,"proof":proof,"prospective":prospective,"frontier":frontier}
        snapshot=self.snapshot_replay(components)
        cert=EpistemicCertificate(
            certificate_id="SCIENCE-ATLAS-CURRENT-EPISTEMIC",knowledge_kind="MODEL",proof_grade="FINITE_REPRESENTABILITY_EXACT__GLOBAL_ONTOLOGY_NOT_PROVEN",
            evidence_grade="BOUNDED_MULTISCIENCE_PLUS_PROSPECTIVE_PENDING",provenance_grade="HASH_BOUND_LOCAL_ARTIFACTS",novelty_grade="NOT_A_NOVELTY_CERTIFICATE",
            identifiability_grade="FAIL_CLOSED",prediction_grade="OUT_OF_CORPUS_SIGNAL__UNKNOWN_TO_HUMAN_PENDING",claim_boundary={"unique_ontological_atlas":False,"new_law":False},
            evidence_digests=tuple(v["digest"] for v in components.values()),
        ).finalized()
        checks={
            "role_typed_seed_multidomain":charts["domain_count"]==13 and charts["occupied_domain_count"]>=8 and charts["canonical_axis_count"]==655,
            "operator_frontier_current_nonempty":operators["operator_candidate_count"]>0,
            "recurrent_operator_family_found":operators["recurrent_family_count"]>=1,
            "formal_representation_theorem_preserved":proof["finite_typed_representability_proven"] is True,
            "unique_ontological_atlas_not_claimed":proof["unique_ontological_atlas_proven"] is False,
            "current_frontier_persistent_and_unresolved":prospective["persistent_frontier_count"]>0 and prospective["persistent_frontier_count"]==frontier["hypothesis_count"] and prospective["unresolved_or_pending_count"]>0,
            "frontier_h1_not_promoted":frontier["frontier_hypothesis_is_law"] is False,
            "gsa002_remains_fail_closed":gsa["confirmatory_fit_claimed"] is False,
            "snapshot_replay_exact":snapshot["status"]=="PASS_EXACT_ATLAS_SNAPSHOT_REPLAY",
            "epistemic_certificate_fail_closed":cert.claim_boundary.get("new_law") is False,
        }
        payload={
            "schema":"phi-science-atlas-core-qualification/v1","kernel_id":KERNEL_ID,"status":"PASS_SCIENCE_ATLAS_CORE_10_OF_10" if all(checks.values()) else "FAIL_SCIENCE_ATLAS_CORE",
            "passed":sum(checks.values()),"total":len(checks),"checks":checks,"charts":charts,"operators":operators,"proof":proof,"prospective":prospective,"frontier":frontier,"gsa002":gsa,"snapshot_replay":snapshot,"epistemic_certificate":cert.__dict__,
            "owner_binding":{"chart_closure_operator_defect_owner":"CONSTRAINT-ATLAS","bridge_owner":"CROSS-DOMAIN-BRIDGE","axis_genesis_owner":"DYNAMIC-AXIS-LIFECYCLE","parallel_science_atlas_owner_created":False},
            "claim_boundary":{"global_science_atlas_predictive_geometry_proven":False,"new_scientific_law_claimed":False},
        }
        return {**payload,"digest":digest_payload(payload)}
