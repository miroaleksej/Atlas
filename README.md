# Atlas


**Φ-Compiler / ScienceAtlas — CURRENT 15.24.0**

<img width="1672" height="941" alt="5e93d208-575f-40f6-84d0-791e947515a5" src="https://github.com/user-attachments/assets/7aa093ac-ba6f-4095-b324-471cc82e4ec3" />

 · ![Python](https://img.shields.io/badge/python-3.11-blue)
 · ![License](https://img.shields.io/badge/license-MIT-green)
 · ![Stars](https://img.shields.io/github/stars/miroaleksej/Atlas)

Atlas is a deterministic, evidence-gated research system for representing scientific quantities, laws, computational methods, hypotheses, experiments, and unresolved research frontiers in one content-addressed state. It combines exact dimensional algebra, adaptive subspace exploration, query-driven candidate generation, domain-specific scientific owners, reproducible numerical qualification, and a fail-closed promotion pipeline.

Atlas addresses a narrower and more rigorous question than “can an AI suggest an equation?”:

> Can a scientific hypothesis be generated, typed, dimensionally qualified, compared with known derivations, bound to measurements, tested out of distribution, calibrated against the complete search procedure, and promoted only when every required evidence gate is satisfied?

The current release is a research system under qualification. It contains no automatically promoted new law and makes no AGI or consciousness claim.

## Contents

- [What Atlas does](#what-atlas-does)
- [Current certified snapshot](#current-certified-snapshot)
- [Scientific claim boundary](#scientific-claim-boundary)
- [Architecture](#architecture)
- [Mathematical foundation](#mathematical-foundation)
- [Dimensional Closure v2.0](#dimensional-closure-v20)
- [Research and promotion pipeline](#research-and-promotion-pipeline)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command-line interface](#command-line-interface)
- [Python API](#python-api)
- [Data and state model](#data-and-state-model)
- [Domain coverage](#domain-coverage)
- [Extending Atlas](#extending-atlas)
- [Hardware-facing workflows](#hardware-facing-workflows)
- [Testing and release verification](#testing-and-release-verification)
- [Repository map](#repository-map)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Citation and provenance](#citation-and-provenance)

## What Atlas does

Atlas provides six connected capabilities.

1. **Persistent scientific address space.** Scientific axes, quantity semantics, units, seven-dimensional SI dimensions, source-law passports, methods, bridges, assumptions, and validity domains are stored as typed records rather than unstructured prose.
2. **Candidate generation.** The system explores combinations of registered axes and qualified source owners, preserves unresolved candidates, and can resume an open-ended fair-dovetail traversal from external state.
3. **Exact dimensional reasoning.** Dimension matrices use exact rational arithmetic over the canonical basis `(L, M, T, I, Θ, N, J)`. Buckingham null spaces are not estimated with floating-point rank heuristics.
4. **Data-facing research.** Given explicit observations and dimensions, Atlas can enumerate a finite subspace surface, freeze dimensionless coordinates, rank target collapse, and replay the entire candidate surface under target permutations.
5. **Scientific adjudication.** A single U0–U10 promotion path separates structural eligibility from empirical evidence. Missing evidence remains pending; it is never silently converted into falsity or acceptance.
6. **Reproducible release control.** Controlled files, canonical JSON digests, manifests, qualification reports, a seal audit, and a strict read-only audit define the shipped state.

Atlas is not a single symbolic-regression routine. It is an ownership and evidence architecture around catalog lookup, dimensional search, model compilation, numerical experiments, prior-art handling, world attestation, resident research state, and release verification.

## Current certified snapshot

The sealed 15.24.0 state contains:

| Item | Current value |
|---|---:|
| Canonical scientific axes | 655 |
| Domain registries | 13 |
| Qualified source-law/owner passports | 445 |
| Computational methods | 24 |
| Active frontier candidates | 4,106 |
| Adaptive multidimensional subspaces | 3,706 |
| Materialized U4 relational hypotheses | 447 |
| U5 collapse/invariance passes | 0 |
| World attestations | 0 |
| Automatic law promotions | 0 |

The scalar-law census over the 3,706 adaptive subspaces contains 683 exact `p = 1` births and 14 distinct canonical π signatures. Within the 447 U4 records, 125 have a frozen `p = 1` candidate and 13 distinct signatures. Candidate count is therefore not treated as mathematical diversity.

The current query-driven synthetic control examined 50 subsets, found 19 one-dimensional null spaces, and deduplicated them to eight mathematical candidates. Without receiving a formula hint, it ranked `L²k/D` first for the Thiele-effectiveness control, with collapse score `0.1059285586`, and replayed the full search surface under 100 target permutations.

The authoritative machine-readable state is [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json), [capabilities.json](capabilities.json), and [invariants.json](invariants.json). Human-readable acceptance evidence is in [ACCEPTANCE_REPORT.md](ACCEPTANCE_REPORT.md).

## Scientific claim boundary

Atlas deliberately separates these statements:

- a record exists;
- a formula is dimensionally admissible;
- a model is structurally lowerable;
- a fit or collapse is good on one dataset;
- a result transfers to a sealed regime;
- a result replicates across independent systems;
- the whole adaptive procedure survives null calibration;
- a discriminating experiment supports the candidate;
- a law candidate may be promoted.

Only the last statement requires every applicable promotion gate. In particular:

- dimensional consistency is necessary, not sufficient;
- a small residual is not a law;
- a frozen π group is a candidate coordinate, not proof of universality;
- literature overlap is not independent evidence;
- absence from a literature search is not proof of novelty;
- retrospective public-data reanalysis is not prospective world attestation;
- synthetic controls verify machinery but do not establish a new physical law;
- an unmaterialized or unevaluated hypothesis is unknown, not false;
- an LLM may propose or explain records but may not stamp `ATLAS_NATIVE`, `ESTABLISHED_LAW`, `CONFIRMED_CONSTANT`, or `EXPERIMENT_PASS`.

The exact allowed claims are frozen in [CLAIM_BOUNDARY.md](CLAIM_BOUNDARY.md). Mathematical and ownership rules are defined by [MATHEMATICAL_CONTRACT.md](MATHEMATICAL_CONTRACT.md) and [MATHEMATICAL_BOOK.md](MATHEMATICAL_BOOK.md).

## Architecture

The main execution path is:

```text
question or dataset
        │
        ▼
typed observables and owner passports
        │
        ▼
adaptive scientific subspaces
        │
        ├── exact dimensional kernel ──► π coordinates / scalar candidates
        ├── representation search ─────► executable formula or operator candidate
        └── domain owners ─────────────► assumptions, limits, predictions
        │
        ▼
frozen candidate + provenance + experiment contract
        │
        ▼
U0 … U10 fail-closed scientific promotion path
        │
        ├── pending: preserve candidate and request missing evidence
        ├── rejected/falsified: preserve receipt and reason
        └── law candidate: only after all required gates pass
```

### Catalog and ownership

`LawSpaceRuntime` loads immutable release data into a `LawCatalog`. Every source law or scientific capability has an owner. An owner passport records its domain, typed symbols, quantity identifiers, formula, dimensions, assumptions, validity region, epistemic state, observables, uncertainty model, and provenance.

This prevents the same printed symbol from being treated as the same physical quantity everywhere and prevents a cross-domain analogy from becoming an identity without a typed bridge. Bare symbols can be ambiguous. `focus_research_question` fails closed when a token maps to multiple quantities and requires a quantity ID or explicit registry entry.

### Canonical axes and candidate subspaces

The primary search space is a registry of scientific coordinates, not an unrestricted expression tree. Candidates bind subsets of axes to qualified owners. A finite run materializes a finite tranche; it does not declare the rest of the scientific space nonexistent.

The fair-dovetail scheduler is append-only and resumable. It has no fixed global scientific step, pair-seed, node-visit, local-shell, or subspace-order ceiling. Per-call budgets bound computation only. Persistent traversal state is written outside the sealed repository.

### Domain bridges

Cross-domain bridges transfer typed structure while preserving source quantities and owners. A bridge may declare a validated symbolic dimension contract or a typed multi-object contract. It does not merge axes merely because their numerical shapes or symbols look similar.

### Representation and theory compilation

Atlas can move from a typed record toward algebraic candidates, scalar π coordinates, operator grammars, domain equations, numerical intermediate representations, compiled theory artifacts, and discriminating experiment plans. Representation diagnostics do not acquire promotion authority merely because they execute successfully.

### Resident research state

The sealed tree is immutable. Long-running cognitive, traversal, and learning state lives under an external state root. The default is:

```text
~/.local/state/phi-compiler/<release>/
```

Set `PHI_STATE_DIR` to choose another external location. If `XDG_STATE_HOME` is set, Atlas uses `$XDG_STATE_HOME/phi-compiler/<release>/`. The runtime rejects mutable state paths inside the sealed release tree.

Resident state is digest-bound. Restore operations require an explicit snapshot and can optionally require an expected SHA-256. Existing state is not overwritten unless `--overwrite-state` is given.

## Mathematical foundation

### Canonical dimension basis

Every physical dimension is a vector in the ordered SI basis

```text
B = (L, M, T, I, Θ, N, J)
```

for length, mass, time, electric current, thermodynamic temperature, amount of substance, and luminous intensity. Legacy five-dimensional descriptors are accepted only at compatibility boundaries; the authoritative kernel is seven-dimensional.

For quantities `q₁, …, qₙ`, Atlas forms the dimension matrix

```text
D = [d(q₁) … d(qₙ)] ∈ ℚ^(7×n).
```

If `r = rank(D)`, the number of independent dimensionless groups is

```text
p = n − r.
```

The null space is computed over rational numbers. A null vector `a` defines

```text
Π = ∏ qᵢ^aᵢ.
```

Atlas canonicalizes a one-dimensional null vector by clearing denominators, dividing by the integer gcd, and fixing the global sign. Equivalent candidates therefore share one π signature.

### The three nullity regimes

- `p = 0`: the supplied quantities contain no dimensionless group. Classical dimensional analysis cannot close the relation from those quantities alone.
- `p = 1`: the dimensionless group is unique up to scale and sign. Atlas may freeze `Π = C_DIMENSIONLESS` as a scalar candidate or `y = f(Π)` when a separate response is supplied.
- `p > 1`: dimensional analysis supplies a family of coordinates but does not select the function relating them. Atlas marks the record `FUNCTION_FORM_REQUIRED_P_GT_1` and delegates representation search to a separately governed owner.

Dimensionless or categorical coordinates are excluded from the physical rank count. Scientific-coordinate IDs are never reinterpreted as physical quantities unless a qualified owner supplies quantity semantics and a dimension.

### Collapse metric

For positive paired coordinate and response values, the operational collapse score bins `log10(Π)`, computes the within-bin standard deviation of `ln(y)`, averages valid bins, and normalizes by the global standard deviation of `ln(y)`.

Lower is better. The current scalar utility owner uses `0.15` as its default threshold, but a passing score still requires out-of-distribution testing and null calibration before scientific promotion.

## Dimensional Closure v2.0

The methodological paper **“Dimensional Closure: Generating a Missing Observable from Data,” version 2.0** extends ordinary dimensional analysis in the reverse direction. Instead of assuming that the observable registry is complete, it asks whether a missing constant or axis can be constructed from measured dependence and then returned to the registry.

This section describes the method and its intended Atlas integration. The current 15.24.0 production owner implements forward exact Buckingham-π birth from already registered, dimensioned quantities. It does **not yet expose the complete inverse missing-constant regression workflow below as a dedicated API owner**. The paper is a validated method specification and control suite; the shipped scalar-law census is a narrower forward implementation.

### Problem statement

Assume a power-law class

```text
y = C ∏ xⱼ^αⱼ,
```

where `y` and `xⱼ` are measured, the exponents `αⱼ` are unknown, and `C` is absent from the input registry. Taking logarithms gives

```text
ln y = β₀ + Σ αⱼ ln xⱼ + ε,
C = exp(β₀).
```

Once the exponent vector is fixed, the missing dimension is unique:

```text
d(C) = d(y) − Σ αⱼ d(xⱼ).
```

The value of the generated quantity is estimated from the same observations:

```text
Ĉᵢ = yᵢ / ∏ xᵢⱼ^αⱼ.
```

The method creates a typed candidate axis with a derived dimension, freezes it before validation, tests whether its estimated value is stable, and only then returns the candidate to the observable registry.

### Identifiability

The exponent vector and intercept are identifiable only when the log-design matrix `[1, ln x₁, …, ln xₘ]` has full column rank `m + 1`. Exact or near collinearity makes individual exponents unstable even when predictions are accurate. Independent predictor variation across broad ranges is essential.

If two missing constants occur only through a product, the data identify the product, not the factors. Dimensional closure can establish that a constant quantity of a particular dimension closes the observed relation; it cannot establish that the quantity is fundamental or uniquely decomposed.

### Six-step closure procedure

1. **Fit the declared class.** Estimate `β₀` and `α` by ordinary least squares in log space, with data selection and transformations frozen.
2. **Rationalize exponents.** Search bounded rational approximations with preregistered numerator, denominator, and tolerance limits.
3. **Compute the missing dimension.** Apply `d(C) = d(y) − Σ αⱼd(xⱼ)` using exact rational dimension vectors.
4. **Register the candidate axis before validation.** Store its dimension, estimated value, uncertainty, source variables, fit specification, and provenance. A nonsimple exponent does not stop this step.
5. **Apply all acceptance criteria.** Measure residual quality, exponent simplicity, and cross-system constancy independently.
6. **Recompute dimensional closure.** Add the generated quantity to the registry and verify that the augmented set has `p = 1` with the frozen identity.

The order is intentional. Rejecting an exponent merely because it looks unfamiliar conflates physical existence with notation preference or measurement uncertainty.

### Three required acceptance criteria

The paper freezes these default thresholds:

| Criterion | Meaning | Default |
|---|---|---:|
| Residual | normalized log-space fit residual | `ρ* = 0.05` |
| Simple exponents | rational bounds and approximation tolerance | `P = 4`, `Q = 2`, `tol = 0.02` |
| Cross-system constancy | dispersion of `ln Ĉ` across independent systems | `σ* = 0.05` |

All three criteria are necessary.

- Residual control rejects noise and relations outside the declared model class.
- Rational simplicity controls the complexity of the proposed exponent structure. An exponent of `1.37` can fit as well as a familiar law and still fail the frozen simple-exponent class.
- Cross-system constancy detects hidden correlated variables and system-specific form factors. A hidden variable can produce small residuals and simple exponents within every system while shifting the inferred constant between systems.

The integer-dimension criterion used in version 1.0 was removed. It was redundant with exponent simplicity and incorrectly rejected valid half-integer laws such as the Kepler relation expressed with `G^−1/2`.

### Control results reported by the paper

The v2.0 study reports:

- recovery of known dimensionless groups for Planck, ideal-gas, Stokes, Kepler, pendulum, Newton, Coulomb, and pipe-flow controls;
- generation of the gravitational-constant dimension `L³ M⁻¹ T⁻²` without providing `G` or its dimension, with estimate `6.6925×10⁻¹¹` versus `6.674×10⁻¹¹` in the synthetic control;
- a preregistered blind set of ten problems with 3 correct acceptances, 7 correct rejections, no false acceptances, and no misses;
- rejection of pure noise, a non-power relation, a nonsimple exponent, system-dependent shape factors, and a worst-case correlated hidden variable;
- a retrospective real-data run over 172 exoplanets around 132 stars, where the generated axis remained stable across four stellar groups with between-group dispersion `0.00085`, while the stellar-mass exponent failed the frozen simplicity tolerance;
- a predeclared shell sequence for `y = f(Π)`: monomial, fractional power, rational Padé, then transcendental atoms.

The real-data outcome is `ACCEPTED_WITH_NONSIMPLE_EXPONENT`, not discovery of a new law. The dataset was selected with knowledge of the contained physics, predictor mass variation was limited, stellar masses were model-derived, and no preregistered unseen-measurement run was performed.

### Adaptive multiplicity

When many variable subsets or representations are searched, the displayed shortlist is not the statistical trial count. The complete frozen pipeline must be replayed on permuted targets. The familywise empirical level is

```text
p_fw = (1 + #{Coll_null ≤ Coll_obs}) / (n_perm + 1).
```

The resolution condition `1/(n_perm + 1) ≤ α` is mandatory. If it fails, the outcome is `INSUFFICIENT_NULL_RESOLUTION`, not pass. Atlas already enforces the same principle in query-driven search and in the U8 whole-pipeline null gate.

### Integration target

A complete production integration of Dimensional Closure v2.0 should add a dedicated owner that:

- accepts a declared target, predictors, dimensions, systems, uncertainties, and frozen thresholds;
- checks positivity, log-design rank, conditioning, and predictor range;
- fits and rationalizes exponents without reading a known answer;
- emits a provisional generated-axis record before adjudication;
- evaluates all three criteria and records every failed criterion;
- runs the full adaptive permutation null when subsets were searched;
- adds an accepted axis only through the existing dynamic-axis lifecycle and U0–U10 promotion authority;
- preserves `ACCEPTED_WITH_NONSIMPLE_EXPONENT`, `INSUFFICIENT_NULL_RESOLUTION`, non-identifiable, and out-of-class outcomes explicitly.

Until that owner exists, callers must not describe the current forward π census as automatic recovery of missing physical constants.

## Research and promotion pipeline

### Query-driven research

`search_observations_for_law_candidates` accepts equally sized observation columns, a seven-component integer dimension for every feature, an optional response, explicit subset-size bounds, a display limit from 10 to 100, and optional permutation settings.

For every feature subset, it computes the exact dimensional null space. Only `p = 1` subsets produce scalar candidates. Mathematical duplicates are merged by canonical signature before ranking.

Without a response, candidates are emitted as `Π = C_DIMENSIONLESS`. With a response, candidates are emitted as `target = f(Π)` and ranked by collapse. When permutations are requested, Atlas replays every deduplicated candidate, not only the displayed rows.

### Representation diagnostics

The π-genesis bridge can freeze a dimensionless coordinate and test bounded monomial/Laurent representations on separate FIT and SEAL partitions. It also provides a bounded Padé-in-`sqrt(Π)` adequacy diagnostic. These routines report representation adequacy only; they do not run the full promotion null and do not promote a law.

### U0–U10 promotion gates

| Gate | Requirement |
|---|---|
| U0 | record integrity and digest validity |
| U1 | typed hypothesis/model binding |
| U2 | exact dimensional qualification |
| U3 | convention and artifact audit |
| U4 | known-derivability and overlap audit |
| U5 | collapse, invariance, or fit evidence |
| U6 | distinct-regime out-of-distribution evidence |
| U7 | cross-system replication |
| U8 | whole-pipeline permutation null |
| U9 | scientifically discriminating experiment |
| U10 | numeric promotion core |

The current census reaches U4 for 447 hypotheses and stops at U5 because the required world evidence is absent. This is expected fail-closed behavior, not a system failure. Weighted scores may rank candidates only after hard gates. A score, AI statement, novelty claim, or expected-information-gain calculation cannot revive a falsified or non-identifiable model.

### Evidence lifecycle

```text
candidate
  → candidate-specific response projection
  → frozen dataset/measurement contract
  → executed measurement response
  → held-out/OOD result
  → independent verification bundle
  → world attestation
  → promotion receipt
```

Digests prevent a post-reveal candidate, projection, dataset, or experiment from being substituted into an earlier receipt. A second manual attempt after failure requires explicit multiplicity and alpha accounting.

## Installation

### Requirements

- Python 3.11 or newer;
- a POSIX-like shell for the supplied `Makefile` commands;
- sufficient memory and CPU for the selected qualification route;
- network access only for initial dependency installation or external scientific resolvers. Core replay uses local artifacts.

Runtime dependencies are declared in [pyproject.toml](pyproject.toml): NumPy, SciPy, SymPy, PyYAML, cryptography, and pypdf.

### Clone and create an environment

```bash
git clone https://github.com/miroaleksej/Atlas.git
cd Atlas
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The repository is currently private, so cloning requires a GitHub identity with access.

### Install the bundled AI research extension

Some autonomous Genesis and research-loop paths import the separately versioned `scienceatlas-ai` component. Install the release-pinned wheel without rebuilding it:

```bash
python -m pip install --no-deps \
  ./extensions/ATLAS_AI_RESEARCH_EXTENSION_v0_10_0/dist/scienceatlas_ai-0.10.0-py3-none-any.whl
```

The component version (`0.10.0`), AI acceptance version (`15.10.5`), component schema (`6.0.0`), state schema (`5`), and Atlas system release (`15.24.0`) are separate identity axes by design.

### Verify installation

```bash
phi-compiler --help
python -c "from source.lawspace.api import LawSpaceAPI; print(LawSpaceAPI('.').runtime.current_release_id())"
make collect
```

Expected release output is `15.24.0`.

## Quick start

### Inspect the law-space catalog

```bash
phi-compiler --mode lawspace-query --query "Kepler" --limit 10
```

```bash
phi-compiler --mode lawspace-query \
  --query "oscillation" \
  --domain physics \
  --limit 20
```

### Search the candidate frontier

```bash
phi-compiler --mode candidate-query --domain physics --limit 20
```

Additional filters are available through `--generator`, `--category`, `--risk`, and `--source-owner`.

### Run an autonomous research question without writing state

```bash
phi-compiler research "What controls reaction-diffusion effectiveness?" \
  --read-only-state \
  --output /tmp/atlas-research.json
```

The command interprets the question and routes it through the resident scientific research cycle. A natural-language question alone does not constitute observational evidence.

### Run with explicit external persistent state

```bash
phi-compiler research "Find unresolved dimensionless transport coordinates" \
  --state-dir /tmp/atlas-state \
  --output /tmp/atlas-research-stateful.json
```

Do not place `--state-dir` inside the repository.

### Run core checks

```bash
make targeted
phi-compiler audit-read-only
```

## Command-line interface

The installed entry point is `phi-compiler`. The equivalent source invocation is `python -m interfaces.phi_compiler_cli`.

### Modern commands

```text
phi-compiler research QUESTION [--read-only-state] [--state-dir DIR] [--output FILE]
phi-compiler resident-state-restore --snapshot FILE [--expected-sha256 HEX]
                                    [--state-dir DIR] [--overwrite-state]
phi-compiler audit-read-only [--output FILE]
```

`research` writes resident state by default. Use `--read-only-state` for exploratory or CI execution. `resident-state-restore` is digest-bound and external-only.

### Catalog and candidate modes

```text
--mode lawspace
--mode lawspace-query       --query TEXT [--domain ID] [--limit N]
--mode candidate-query      [--domain ID] [--generator ID]
                            [--category NAME] [--risk CLASS]
                            [--source-owner ID] [--limit N]
--mode candidate-scan
--mode candidate-regenerate
```

`candidate-scan` regenerates candidates in memory and compares their IDs and digests with the persisted ledger. `candidate-regenerate` writes generated state and should be used only when preparing a new snapshot.

### Computational-method modes

```text
--mode quantum-method-query [--capability NAME] [--limit N]
--mode quantum-method-scan  [--max-order N] [--combination-budget N]
```

Omitting `--max-order` scans all registered method orders. A finite `--combination-budget` is a compute guard, not a scientific-space bound. If insufficient, Atlas exits with status 2 and reports `BLOCKED_INSUFFICIENT_COMBINATION_BUDGET`.

### Qualification and hardware modes

```text
--mode synthetic       [--repeats N] [--workers N] [--shard-size N]
--mode hardware-twin
--mode physical-prebuild [--contract FILE]
--mode physical-adapter  [--contract FILE]
--mode physical-open-loop --contract FILE --host HOST \
                          --expected-serial SERIAL --raw-output FILE \
                          --operator-approved
--mode all-offline
```

With no command or mode, the CLI runs `all-offline`: law-space qualification, synthetic benchmarks, hardware digital twin, physical prebuild checks, and adapter contract checks. It does not run the real-device open-loop path. `--output FILE` writes JSON; otherwise JSON is printed to standard output.

## Python API

`LawSpaceAPI` is the supported programmatic facade.

### Open a runtime and search entities

```python
from source.lawspace.api import LawSpaceAPI

api = LawSpaceAPI(".")
print(api.runtime.current_release_id())

rows = api.search_entities("Kepler", domain_id="astronomy", limit=10)
for row in rows:
    print(row)
```

### Focus a question with explicit observables

```python
focus = api.focus_research_question(
    question="What controls reaction-diffusion effectiveness?",
    named_observables=["Q-DIFFUSIVITY", "Q-LENGTH", "Q-RATE-CONSTANT"],
    expansion_limit=30,
)
print(focus["status"])
```

Prefer quantity IDs. A short symbol such as `D`, `L`, or `k` may be ambiguous across owner passports and will fail closed.

### Search observations for dimensionless candidates

```python
import numpy as np
from source.lawspace.api import LawSpaceAPI

rng = np.random.default_rng(11)
n = 360
D = 10 ** rng.uniform(-12, -8, n)
L = 10 ** rng.uniform(-5, -2, n)
k = 10 ** rng.uniform(-3, 1, n)
pi = L**2 * k / D
eta = np.tanh(np.sqrt(pi)) / np.sqrt(pi)

api = LawSpaceAPI(".")
result = api.search_observations_for_law_candidates(
    observations={"k": k, "D": D, "L": L, "eta": eta},
    dimensions={
        "k": [0, 0, -1, 0, 0, 0, 0],
        "D": [2, 0, -1, 0, 0, 0, 0],
        "L": [1, 0, 0, 0, 0, 0, 0],
    },
    target_name="eta",
    question="What controls reaction-diffusion effectiveness?",
    return_limit=25,
    max_subset_size=3,
    permutation_count=100,
    permutation_seed=99,
)
print(result["candidates"][0])
print(result["permutation_null"])
```

All columns must have equal length. Collapse requires positive coordinate and target values. Every feature needs exactly seven integer dimension components.

### Inspect the frozen scalar-law census

```python
census = api.get_scalar_law_birth_current()
print(census["status"])
print(census["summary"])
```

The method verifies the embedded digest before returning the artifact.

### API authority classes

- `READ_TOOLS`: catalog, contracts, current state, research, qualification, and diagnostics;
- `MUTATION_TOOLS`: explicit state-changing research, ontology, axis, measurement, resident, and traversal operations;
- `REGRESSION_TOOLS`: answer-bearing or post-freeze controls requiring `regression_mode=True`.

Regression surfaces are excluded from default blind research. AI proposals are restricted to pending states and cannot directly mutate the active scientific registry.

## Data and state model

The repository stores typed artifacts for canonical and dynamic axes; quantity definitions and SI dimensions; source-law passports and constants; domain and integration manifests; active frontier candidates; computational methods and routes; evidence, trust, source snapshots, formal contracts; frozen research examples and measurement requests; and qualification reports.

Records are content-addressed with canonical SHA-256 digests. Parent artifacts bind child identities so that a changed candidate, dataset, response projection, or result invalidates downstream receipts.

Mutable research state is excluded from the release seal. Configure it with:

```bash
export PHI_STATE_DIR=/absolute/path/outside/Atlas
```

Use a dedicated path per operator or environment. Back up both state JSON and its expected digest before migration.

Generated controls are:

- [HASHES.txt](HASHES.txt): controlled file hashes;
- [FILE_TREE.md](FILE_TREE.md): controlled tree;
- [RELEASE_MANIFEST.json](RELEASE_MANIFEST.json): release identities, files, census, reports, and policies;
- [capabilities.json](capabilities.json): executable capabilities and counts;
- [invariants.json](invariants.json): negative and safety invariants.

Do not hand-edit generated digests. Change the source artifact, run qualification, and rebuild controls.

## Domain coverage

The passport catalog covers physics, mechanics, chemistry, astronomy, materials science, aeronautics and aerostation, mathematics, metrology, and systems/control, with additional registries and specialized owners providing the full 13-domain release census.

Major executable owner families include exact axis/law-space search; mechanics and aeronautics; atomic electronic and many-body state spaces; nuclear binding/decay evidence; neutrino likelihoods; particle-space and collider qualification; black-hole, Einstein, tensor-geometry, and curvature-memory controls; quantum-vacuum/gravity intersections; pharmaceutical workflows; mathematical invention and theory compilation; experiment design; and cognitive, resident, knowledge-evolution, reflexive, developmental, and self-repair owners.

An executable owner is not an empirically established result. Every output carries its own status and claim boundary.

## Extending Atlas

### Add a domain plugin

`data/domains/*.json` is the declarative registration point. Start from `data/domains/domain_manifest.template.json.txt`.

A manifest must provide `schema = phi-domain-plugin-manifest/v1`, a unique `domain_id`, `common_rules_owner = COMMON-SCIENTIFIC-RULES/1.0.0`, and domain-specific axes. It may name an importable owner module/class for equations, semantic transforms, compatibility logic, or experiments.

Do not copy shared evidence, verification, novelty, information-gain, or promotion rules into a domain. Restart the process after changing a manifest; a frozen runtime never changes its axis space in place.

### Add a source-law passport

Include stable owner and quantity IDs, exact symbol dimensions, a parseable formula, assumptions, validity domain, uncertainty model, observables, controlled limits, and provenance. Add tests for parsing, dimensional consistency, owner registration, and bridges.

### Add a representation grammar

A new grammar needs bounded enumeration, a complexity measure, separate fit and seal partitions, multiplicity/null accounting, and a promotion boundary. A diagnostic helper cannot become a live scientific grammar merely by registration.

### After any controlled change

```bash
make collect
make targeted
pytest -q -p no:cacheprovider
make release-controls
make seal-audit
make audit-read-only
```

## Hardware-facing workflows

Hardware support is centered on [hardware/PHYSICAL_STAND.json](hardware/PHYSICAL_STAND.json), [hardware/PHYSICAL_STAND.md](hardware/PHYSICAL_STAND.md), and the RLC digital-twin circuit.

The safety sequence is: run the digital twin; run prebuild qualification; validate the adapter/relay contract; verify host and expected serial; require operator approval; write raw output to the declared path; then evaluate it under the evidence rules.

`physical-open-loop` never runs as part of default `all-offline`. Do not use a real device unless its contract, serial, operating limits, isolation, and operator authorization have been independently checked.

## Testing and release verification

### Fast checks

```bash
make collect
make targeted
```

### Full pytest suite

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 \
OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
pytest -q -p no:cacheprovider
```

The release has been qualified at 90/90 tests.

### Native experiment and qualification targets

```bash
make first-experiment
make real-experiment
make frontier-scan
make science-atlas
make self-repair
make qualify
```

These targets have different costs and mutation behavior. `frontier-scan`, `self-repair`, and `qualify` regenerate controlled reports or state and are release-maintenance operations.

### Heavy fresh-process replay

```bash
make full
```

This prepares a replay plan, executes isolated batches, and aggregates `reports/FULL_HEAVY_REPLAY_CURRENT.json`.

### Rebuild and audit the release seal

```bash
make release-controls
make seal-audit
make audit-read-only
```

`release-controls` regenerates the manifest, capabilities, invariants, hashes, and tree after an intentional controlled change. The seal audit reports `PASS_SEAL_AUDIT` when identities match. The strict audit verifies that read-only execution creates no bytecode, report, cache, or mutable state in the release and reports `PASS_READ_ONLY_AUDIT`.

### Clean transient files

```bash
make clean
```

This removes caches, bytecode, and selected generated reports. Rebuild required reports and release controls afterward.

## Repository map

```text
Atlas/
├── source/lawspace/        scientific owners, runtime, API, schemas, kernels
├── interfaces/             command-line entry point
├── evaluation/             qualification, replay, benchmarks, release controls
├── tests/                  current-state behavioral and integrity tests
├── data/                   axes, quantities, passports, domains, frontiers, evidence
├── extensions/             separately versioned Atlas AI component
├── hardware/               physical-stand contracts and digital twin
├── external/               external adapters/artifacts included in the seal
├── reports/                current qualification and diagnostic reports
├── static/                 static resources
├── MATHEMATICAL_BOOK.md     complete mathematical reference
├── MATHEMATICAL_CONTRACT.md normative mathematical contract
├── CLAIM_BOUNDARY.md        allowed and forbidden scientific claims
├── ACCEPTANCE_REPORT.md     current acceptance evidence
├── RELEASE_MANIFEST.json    release identity and controlled-file ledger
├── capabilities.json        machine-readable capability census
├── invariants.json          machine-readable safety invariants
├── HASHES.txt               controlled SHA-256 list
├── FILE_TREE.md             controlled repository tree
├── Makefile                 standard operational targets
└── pyproject.toml           Python package metadata and dependencies
```

Use [FILE_TREE.md](FILE_TREE.md) for the exact sealed file list.

## Limitations

- No new universal physical law has been established.
- No current candidate has passed U5–U10; there is no world attestation or automatic promotion.
- The Dimensional Closure v2.0 inverse missing-constant workflow is documented but is not yet a dedicated production owner.
- `p > 1` systems need an external representation principle or controlled function search.
- Correlated hidden variables can mimic simple power laws without independent systems.
- Poor predictor range and measurement error can bias recovered exponents.
- Constants occurring only as a product cannot be individually identified.
- Permutation counts must support the intended significance resolution.
- The per-target permutation e-process is not an Atlas-wide global online error controller.
- Search is open-ended in policy, but every actual run is finite and resource-bounded.
- Quarantining known-law fixtures is not proof of novelty.
- Domain coverage is broad but incomplete and depends on passport and evidence quality.

## Troubleshooting

### `ModuleNotFoundError: scienceatlas_ai`

Install the bundled wheel shown in [Installation](#install-the-bundled-ai-research-extension).

### Research state path is rejected

The path resolves inside the sealed repository. Set `PHI_STATE_DIR` or `--state-dir` to an absolute external directory.

### A symbol is ambiguous

Use the canonical quantity ID instead of a one-letter display symbol. Inspect passports with `lawspace-query` or API methods `get_quantity` and `resolve_symbol`.

### No scalar candidate is returned

- `p = 0`: no dimensionless group exists in the supplied dimensions.
- `p > 1`: dimensions do not select a unique scalar relation.
- Dimensionless or untyped quantities may have been excluded from rank.

### Collapse scoring raises an error

The metric requires positive paired values, equal column lengths, nonzero target log-variance, and enough populated logarithmic bins.

### Permutation resolution is insufficient

Increase `permutation_count` until `1/(n_perm + 1) ≤ α`. Insufficient resolution is not a pass.

### Quantum method scan exits with code 2

Increase the explicit combination budget or omit it to scan the complete registered finite surface.

### Seal audit fails after an edit

If intentional, run relevant tests and qualifications, then `make release-controls` and both audits. Otherwise inspect `git diff`, [HASHES.txt](HASHES.txt), and the manifest first.

## Citation and provenance

For the system, cite the exact release and manifest digest:

```text
Atlas / Φ-Compiler / ScienceAtlas, system release 15.24.0,
RELEASE_MANIFEST.json and controlled SHA-256 ledger.
```

For the inverse method:

```text
“Dimensional Closure: Generating a Missing Observable from Data,” version 2.0.
```

The manuscript’s appendix names `frozen_rule.py`, `inv.py`, `invent.py`, `ctrl.py`, `exp1.py`–`exp4.py`, and `kepler/` reproduction artifacts. Those belong to the manuscript package and are not claimed to be in this repository unless explicitly imported and sealed later.

No `LICENSE` file is present in this snapshot. Possession of the source does not by itself grant redistribution or modification rights; obtain permission from the repository owner before external reuse.
