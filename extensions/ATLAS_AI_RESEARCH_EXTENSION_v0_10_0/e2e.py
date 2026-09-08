import sys, random
sys.path.insert(0, "src")
from fractions import Fraction
from scienceatlas_ai.runtime import ScienceAtlasAI
from scienceatlas_ai.types import (
    Observation, EvidenceRecord, SemanticQuantity, ValidityDomain, ValidationOutcome,
)
from scienceatlas_ai.continual import GenesisState, RegionalMetaLearner
from scienceatlas_ai.research_loop import (
    AcquisitionRequest, LoopBudget, LoopState, ResearchLoopOwner, source_spec,
)
from scienceatlas_ai.system import ResearchSystem
from scienceatlas_ai.operator_genesis import (
    GenesisBudget, GenesisSplit, OperatorGenesisOwner, OperatorGrammar,
)
from scienceatlas_ai.methodology import PipelineNullCalibrationOwner
from scienceatlas_ai.owners import _least_squares, DetachedOwner

DOM = "toy"
UNIT = {"x": "m", "z": "m", "y": "J"}


def quantity(axis, value):
    return SemanticQuantity(value=Fraction(value), semantic_type="scalar", domain=DOM, unit=UNIT[axis])


class ToySource:
    """Ground truth y = 3x^2 - 2z. Declared as a fixture, not a measurement."""

    spec = source_spec(
        source_id="toy-quadratic",
        real_measurement=False,
        validity_domain="synthetic toy relation for loop verification only",
    )

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.calls = 0

    def acquire(self, request: AcquisitionRequest):
        self.calls += 1
        if request.point is None:
            xs = {"x": Fraction(self.rng.randint(1, 9)), "z": Fraction(self.rng.randint(1, 5))}
        else:
            xs = {k: q.value for k, q in request.point.items()}
            for axis in ("x", "z"):
                xs.setdefault(axis, Fraction(self.rng.randint(1, 5)))
        y = 3 * xs["x"] * xs["x"] - 2 * xs["z"]
        out = []
        for axis, value in (("x", xs["x"]), ("z", xs["z"]), ("y", y)):
            ev = EvidenceRecord(
                evidence_id=f"ev-{request.sample_id}-{axis}",
                source="toy-quadratic",
                source_class="fixture",
                reliability_bp=10_000,
                claim=f"{axis}={value} for {request.sample_id}",
            )
            out.append((Observation(request.sample_id, axis, quantity(axis, value), ev.evidence_id), ev))
        return tuple(out)


def build():
    ai = ScienceAtlasAI()
    for axis in ("x", "z", "y"):
        ai.birth_axis(axis_id=axis, name=axis, semantic_type="scalar", domain=DOM, unit=UNIT[axis])
    return ai


print("=" * 62)
print("1. LOOP: closed observe->hypothesize->act->measure->learn")
print("=" * 62)
ai = build()
system = ResearchSystem(
    ai=ai,
    loop_budget=LoopBudget(max_steps=14, max_acquisitions=40, patience=4, min_success_gain_bp=1_000),
)
system.loop_state.target_pool = ("y",)
source = ToySource(seed=3)
loop = system.loop()
summary = loop.run(
    ai=ai, source=source, state=system.loop_state,
    meta=system.meta, genesis=system.genesis,
)
print("stop:", summary["stop_reason"], "| steps:", summary["steps_executed"], "| acquisitions:", summary["acquisitions"])
print("statuses:", summary["statuses"])
print("observations now:", len(ai.world.observations), "| samples:", len(ai.world.sample_ids()))
print("scalar meta:", ai.meta.to_json()["scores_bp"])
print("regional meta (numeric owner, default/toy):",
      system.meta.score_bp("multi-axis-mechanism-owner/1.0.0", regime="default", domain=DOM))
print("alpha balance bp:", system.genesis.ledger.balance_bp)

print()
print("=" * 62)
print("2. GENESIS: promote an operator the incumbents cannot express")
print("=" * 62)
rows = []
for sid in ai.world.sample_ids():
    vals = {a: ai.world.values_by_sample(a).get(sid) for a in ("x", "z", "y")}
    if all(v is not None for v in vals.values()):
        rows.append(({"x": vals["x"], "z": vals["z"]}, vals["y"]))
print("usable rows:", len(rows))
cut = max(2, len(rows) * 2 // 3)
fit, seal = rows[:cut], rows[cut:]


def incumbent_fit(rf, rs):
    M = [[xs["x"], xs["z"], Fraction(1)] for xs, _ in rf]
    p = _least_squares(M, [y for _, y in rf])
    if p is None:
        return None
    tot = Fraction(0)
    for xs, y in rs:
        tot += (y - (p[0] * xs["x"] + p[1] * xs["z"] + p[2])) ** 2
    return tot


grammar = OperatorGrammar(max_terms=3, max_degree=2)
budget = GenesisBudget(grammar=grammar, max_families_examined=400, permutation_count=20, alpha_bp=500)
split = GenesisSplit(
    propose=("p0",),
    fit=tuple(f"f{i}" for i in range(len(fit))),
    seal=tuple(f"s{i}" for i in range(len(seal))),
)
genesis_owner = OperatorGenesisOwner(null_owner=PipelineNullCalibrationOwner())


def null_replay(seed):
    rng = random.Random(seed)
    ys = [y for _, y in rows]
    rng.shuffle(ys)
    permuted = [(xs, y) for (xs, _), y in zip(rows, ys)]
    c = genesis_owner.run(
        target_axis="y", input_axes=("x", "z"),
        rows_fit=permuted[:cut], rows_seal=permuted[cut:],
        budget=GenesisBudget(grammar=grammar, max_families_examined=400, permutation_count=1),
        split=split, incumbent_fit=incumbent_fit, incumbent_owner_ids=("inc",),
    )
    return Fraction(c.sealed_gain_bp)


system.genesis.ledger.grant_for_samples(
    [f"seed-{i}" for i in range(60)], domain=DOM, axes=("x", "z", "y"),
    evidence_fingerprints={f"seed-{i}": f"fixture-seed-evidence-{i}" for i in range(60)},
)
cert = genesis_owner.run(
    target_axis="y", input_axes=("x", "z"), rows_fit=fit, rows_seal=seal,
    budget=budget, split=split, incumbent_fit=incumbent_fit,
    incumbent_owner_ids=("multi-axis-mechanism-owner/1.0.0",),
    null_replay=null_replay, null_seeds=list(range(20)),
    ledger=system.genesis.ledger, journal=system.genesis.journal, search_domain=DOM,
)
print("certificate:", cert.status, "| sealed gain bp:", cert.sealed_gain_bp)
print("family:", cert.family.to_json()["terms"])

owner, receipt = system.genesis.promote(
    cert, budget=budget, bus=ai.owner_bus, meta=system.meta, regime="default", domain=DOM,
)
print("promotion:", receipt["status"], "|", receipt.get("owner_id"))
print("alpha after promotion:", system.genesis.ledger.balance_bp)
print("quarantined (credit blocked):", not system.genesis.credit_allowed(owner.spec.owner_id))
print("entered meta at bp:", system.meta.score_bp(owner.spec.owner_id, regime="default", domain=DOM))

hyps = owner.propose(rows, input_axes=("x", "z"), target_axis="y", provenance=("loop",))
print("synthesized params:", [str(p) for p in hyps[0].parameters], "(truth: -2, 3)")
print("predict x=12,z=4:", owner.predict(hyps[0], {"x": Fraction(12), "z": Fraction(4)}),
      "| truth:", 3 * 144 - 8)

print()
print("=" * 62)
print("3. PERSIST + RESTART: rehydration of the synthesized owner")
print("=" * 62)
root_before = system.composite_root()
system.save("/tmp/system_state.json")
restored, rehydration = ResearchSystem.load("/tmp/system_state.json")
print("composite root preserved:", restored.composite_root() == root_before)
print("rehydrated:", rehydration["attached"])
live = restored.ai.owner_bus.get(owner.spec.owner_id)
print("owner is live (not detached):", not isinstance(live, DetachedOwner), "|", type(live).__name__)
h2 = live.propose(rows, input_axes=("x", "z"), target_axis="y", provenance=("restored",))
print("predicts after restart:", live.predict(h2[0], {"x": Fraction(12), "z": Fraction(4)}))
print("alpha ledger survived:", restored.genesis.ledger.balance_bp)
print("regional scores survived:",
      restored.meta.score_bp(owner.spec.owner_id, regime="default", domain=DOM))

print()
print("=" * 62)
print("4. REVOCATION: three consecutive prospective failures")
print("=" * 62)
plan = restored.ai.design_multiaxis_experiment(input_axes=("x", "z"), target_axis="y", intervention_axis="x")
exp_id = plan.experiment_id if plan is not None else list(restored.ai.experiments)[0]
for i in range(3):
    bad = ValidationOutcome(
        experiment_id=exp_id, owner_id=owner.spec.owner_id,
        success=False, prediction_gain_bp=0, notes=f"synthetic failure {i}",
    )
    restored.ai.record_validation(bad)
    restored.meta.update(bad, regime="default", domain=DOM)
    print(f"  failure {i+1}:", restored.genesis.observe_outcome(bad))
print("active synthesized owners:", restored.genesis.active_owner_ids())
print("revoked:", restored.genesis.revoked_owner_ids)
print("certificate status:", restored.genesis.certificates[cert.digest].status)
print("owner still registered on bus (history not rewritten):",
      owner.spec.owner_id in [s.owner_id for s in restored.ai.owner_bus.specs()])

print()
print("status:", {k: v for k, v in restored.status().items() if k not in {"digest"}})
