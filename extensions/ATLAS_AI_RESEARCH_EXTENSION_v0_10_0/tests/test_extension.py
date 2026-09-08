from __future__ import annotations
import csv, pathlib, sys, unittest
from fractions import Fraction
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scienceatlas_ai import ScienceAtlasAI
from scienceatlas_ai.ai_lab import ModelBackendSpec, ModelScale, BUDGET_CAPABILITIES, REGIME_CAPABILITIES
from scienceatlas_ai.frontier003 import load_manifest
from scienceatlas_ai.continual import AlphaLedger, GenesisState
from scienceatlas_ai.genesis_shells import ShellLadder, SearchPricing
from scienceatlas_ai.methodology import PipelineNullCalibrationOwner
from scienceatlas_ai.operator_genesis import GenesisSplit, OperatorGenesisOwner
from scienceatlas_ai.owners import _least_squares

class ExtensionTests(unittest.TestCase):
    def test_frozen_frontier003_shape(self):
        manifest = load_manifest(ROOT / "frontier003" / "RUN_MANIFEST.csv")
        self.assertEqual(len(manifest), 168)
        with (ROOT / "frontier003" / "RESULTS_TEMPLATE.csv").open(newline="", encoding="utf-8") as h:
            self.assertEqual(len(list(csv.DictReader(h))), 672)

    def test_fail_closed_without_backend(self):
        ai = ScienceAtlasAI()
        self.assertEqual(ai.ai_laboratory_status()["status"], "MEASUREMENT_BACKEND_GAP")

    def test_backend_spec_contract(self):
        spec = ModelBackendSpec(
            backend_id="test", model_family_id="family", architecture_id="arch",
            scales=(ModelScale("SMALL", 1_000_000_000), ModelScale("REFERENCE", 4_000_000_000), ModelScale("LARGE", 16_000_000_000)),
            supported_budget_capabilities=tuple(BUDGET_CAPABILITIES.values()),
            supported_regimes=tuple(REGIME_CAPABILITIES), real_measurement=False,
        )
        self.assertEqual(set(spec.scale_map()), {"SMALL","REFERENCE","LARGE"})
        self.assertFalse(spec.real_measurement)

    def test_alpha_ledger_persistent_dedup_and_support(self):
        ledger = AlphaLedger()
        ledger.grant_for_samples(["s1"], domain="A", axes=("x", "y"), evidence_fingerprints={"s1": "ev-1"})
        self.assertEqual(ledger.balance_bp, 25)
        ledger.grant_for_samples(["s1"], domain="A", axes=("x", "y"), evidence_fingerprints={"s1": "ev-1"})
        self.assertEqual(ledger.balance_bp, 25)
        # New sample alias, same persistent evidence identity: no new alpha.
        ledger.grant_for_samples(["alias-1"], domain="A", axes=("x", "y"), evidence_fingerprints={"alias-1": "ev-1"})
        self.assertEqual(ledger.balance_bp, 25)
        # Scoped grants without a stable evidence fingerprint fail closed.
        ledger.grant_for_samples(["missing"], domain="A", axes=("x", "y"))
        self.assertEqual(ledger.balance_bp, 25)
        restored = AlphaLedger.from_json(ledger.to_json())
        restored.grant_for_samples(["alias-after-restart"], domain="A", axes=("x", "y"), evidence_fingerprints={"alias-after-restart": "ev-1"})
        self.assertEqual(restored.balance_bp, 25)
        self.assertFalse(restored.can_spend(25, domain="B", axes=("x", "y")))
        self.assertFalse(restored.can_spend(25, domain="A", axes=("x", "z")))
        self.assertTrue(restored.can_spend(25, domain="A", axes=("x", "y")))
        self.assertEqual(restored.spend(25, purpose="test", domain="A", axes=("x", "y"))["status"], "SPENT")
        self.assertEqual(restored.balance_bp, 0)

    def test_unbounded_shell_diagnostic_and_bounded_materialisation(self):
        ladder = ShellLadder(); pricing = SearchPricing()
        price70 = pricing.search_price_bp(families_charged=ladder.shell(70).max_families_examined, permutation_count=1)
        self.assertEqual(ladder.deepest_affordable(pricing=pricing, balance_bp=price70, permutation_count=1), 70)
        grammar = ladder.shell(20).grammar
        atoms = grammar._atomic_terms(tuple(f"a{i}" for i in range(40)), max_atoms=64)
        self.assertEqual(len(atoms), 64)
        self.assertEqual(atoms, tuple(sorted(atoms, key=lambda t: (t.degree, t.powers))))

    def test_duplicate_search_is_zero_cost(self):
        owner = OperatorGenesisOwner(null_owner=PipelineNullCalibrationOwner())
        ladder = ShellLadder(); shell = ladder.shell(0); pricing = SearchPricing()
        rows = [({"x": Fraction(i)}, Fraction(2*i)) for i in range(1, 7)]
        split = GenesisSplit(propose=("p",), fit=("f1","f2","f3"), seal=("s1","s2","s3"))
        def incumbent(rf, rs):
            p = _least_squares([[q["x"], Fraction(1)] for q,_ in rf], [y for _,y in rf])
            return sum((y-(p[0]*q["x"]+p[1]))**2 for q,y in rs) if p else None
        state = GenesisState(ledger=AlphaLedger())
        state.ledger.grant_for_samples(
            [f"d{i}" for i in range(20)], domain="D", axes=("x","y"),
            evidence_fingerprints={f"d{i}": f"ev-d-{i}" for i in range(20)},
        )
        budget = shell.budget(permutation_count=1)
        owner.run(target_axis="y", input_axes=("x",), rows_fit=rows[:3], rows_seal=rows[3:], budget=budget,
                  split=split, incumbent_fit=incumbent, incumbent_owner_ids=("i",), shell=shell,
                  ledger=state.ledger, journal=state.journal, pricing=pricing, search_domain="D")
        before = state.ledger.balance_bp
        cert = owner.run(target_axis="y", input_axes=("x",), rows_fit=rows[:3], rows_seal=rows[3:], budget=budget,
                  split=split, incumbent_fit=incumbent, incumbent_owner_ids=("i",), shell=shell,
                  ledger=state.ledger, journal=state.journal, pricing=pricing, search_domain="D")
        self.assertEqual(dict(cert.gates).get("SEARCH_NOVELTY"), "FAIL_DUPLICATE_SEARCH")
        self.assertEqual(state.ledger.balance_bp, before)

if __name__ == "__main__": unittest.main()
