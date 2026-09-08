from __future__ import annotations
import argparse, csv, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from scienceatlas_ai import ScienceAtlasAI
from scienceatlas_ai.ai_lab import REQUIRED_FRONTIER_CAPABILITIES
from scienceatlas_ai.frontier003 import load_manifest
from scienceatlas_ai.continual import GenesisState, RegionalMetaLearner
from scienceatlas_ai.operator_genesis import OperatorGenesisOwner
from scienceatlas_ai.research_loop import ResearchLoopOwner
from scienceatlas_ai.system import ResearchSystem
from scienceatlas_ai.permutation_eprocess import PermutationEProcessOwner, PermutationEProcessState

parser=argparse.ArgumentParser()
parser.add_argument('--atlas-root', default='')
args=parser.parse_args()
manifest = load_manifest(ROOT / "frontier003" / "RUN_MANIFEST.csv")
with (ROOT / "frontier003" / "RESULTS_TEMPLATE.csv").open(newline="", encoding="utf-8") as h:
    rows = list(csv.DictReader(h))
ai = ScienceAtlasAI()
status = ai.ai_laboratory_status()
assert ai.VERSION == '0.10.0', ai.VERSION
assert len(manifest) == 168, len(manifest)
assert len(rows) == 672, len(rows)
assert status["status"] == "MEASUREMENT_BACKEND_GAP", status
for cap in REQUIRED_FRONTIER_CAPABILITIES:
    assert cap in status["required_frontier_capabilities"], cap
assert OperatorGenesisOwner is not None and ResearchLoopOwner is not None
assert GenesisState is not None and RegionalMetaLearner is not None and ResearchSystem is not None
assert PermutationEProcessOwner is not None and PermutationEProcessState is not None
out={
    "status": "PASS",
    "ai_version": ai.VERSION,
    "manifest_rows": len(manifest),
    "measurement_slots": len(rows),
    "laboratory_status": status["status"],
    "required_frontier_capabilities": len(REQUIRED_FRONTIER_CAPABILITIES),
    "operator_genesis_available": True,
    "closed_research_loop_available": True,
    "composite_persistence_available": True,
    "permutation_eprocess_available": True,
}
if args.atlas_root:
    receipt=ai.mount_atlas(args.atlas_root)
    overlay=ai.atlas_qualified_owner_axis_bindings()
    bridge=ai.atlas_bridge_typing_audit()
    frontier=ai.atlas_frontier_probe()
    assert receipt['registry_snapshot']['axis_count'] == 655
    assert receipt['mounted_passport_owner_count'] == 445
    assert receipt['qualified_owner_axis_binding_count'] == 3
    assert overlay['count'] == 3
    # qualified same-domain semantic bindings must not be silently promoted to cross-domain routes
    assert bridge['fully_typed_bridge_count'] == 0
    out['atlas_mount']={
        'release':receipt['registry_snapshot']['release_identity']['release'],
        'axis_count':receipt['registry_snapshot']['axis_count'],
        'passport_count':receipt['mounted_passport_owner_count'],
        'mounted_owner_count':receipt['mounted_owner_count'],
        'qualified_owner_axis_binding_count':overlay['count'],
        'bridge_status':bridge['status'],
        'fully_typed_bridge_count':bridge['fully_typed_bridge_count'],
        'frontier_status':frontier['status'],
        'mutation_policy':receipt['mutation_policy'],
    }
print(json.dumps(out, sort_keys=True))
