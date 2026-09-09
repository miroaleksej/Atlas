# MATHEMATICAL CONTRACT — Φ-Compiler CURRENT 0.15.27.0

## 1. Current authority

Единственный current owner общенаучной оркестрации:

```text
ADAPTIVE-RESEARCH-KERNEL/15.4.0
```

`SCIENTIFIC-RESEARCH-CYCLE/15.2.8` является compatibility facade к существующим специализированным surfaces и не имеет права самостоятельно выпускать `ATLAS_NATIVE` claims.

## 2. State

На цикле `k` состояние исследований:

```math
S_k=(D_k,\mathcal A_k,\mathcal L_k,\mathcal H_k,\mathcal E_k,\Pi_k),
```

где:

- `D_k` — наблюдения и provenance;
- `A_k` — current canonical + research-local axes;
- `L_k` — текущий математический язык/representation;
- `H_k` — hypothesis population;
- `E_k` — evidence/residual/experiment ledger;
- `Π_k` — claim/provenance state.

## 3. Axis-space contract

```math
|\mathcal A_k|<\infty
```

для конкретного вычислительного шага, но глобального значения

```math
\sup_k|\mathcal A_k|
```

система не задаёт.

Разрешены переходы:

```math
\mathcal A_k\to\mathcal A_k\cup\{a\}
```

```math
a\to(a_1,a_2)
```

```math
(a_1,a_2)\to a
```

```math
a\to\varnothing
```

при наличии квалифицированного Axis Lifecycle receipt.

Текущая 655 canonical axis — address-space snapshot, не универсальная размерность.

### 3.1 Active / dormant distinction

Наблюдаемая ось может присутствовать в research representation и одновременно отсутствовать в текущей формуле:

```math
\mathcal A_k=\mathcal A_k^{active}\cup\mathcal A_k^{dormant}.
```

`dormant`-ось не передаётся hypothesis synthesizer. Её активация допускается только после residual-driven AxisDiscovery evidence и должна улучшать независимую predictive проверку. Простое предложение пользователя/ИИ «добавить temperature» не является разрешением вставить `T` в формулу.

## 4. Hypothesis language

Для target `y` и observables `x_i` Atlas может строить typed constructions. В текущем executable shell реализована fair-dovetail family мономов:

```math
m_{\mathbf p}(x)=\prod_i x_i^{p_i},\qquad p_i\in\mathbb N_0,
```

по одному суммарному complexity degree на цикл.

Модель:

```math
\hat y=c_0+\sum_j c_jm_j(x).
```

Размерностное замыкание:

```math
D(c_j)=D(y)-D(m_j),
```

```math
D(m_j)=\sum_i p_{ji}D(x_i).
```

Это означает, что bare-addition несовместимых величин запрещено типовой алгеброй, но Atlas может породить коэффициент/масштаб, если такой кандидат фальсифицируем.

Глобального fixed complexity ceiling нет. Каждый шаг исследует одну конечную оболочку; следующий шаг может открыть следующую.

## 5. Residual

```math
r_i=y_i-\hat y_i.
```

Residual не является автоматическим `FAIL`. Он является evidence для одного из переходов:

```text
KEEP REPRESENTATION
BIRTH AXIS
SPLIT/MERGE/RETIRE AXIS
OPEN NEXT HYPOTHESIS SHELL
INVENT REPRESENTATION PRIMITIVE
DESIGN DISCRIMINATING EXPERIMENT
```

Ручные element/case-specific exceptions не являются общим механизмом Research Kernel.

## 6. Candidate lifecycle

Обязательная семантика:

```text
IDEA
CANDIDATE
TESTABLE
SURVIVOR
LAW-CANDIDATE
PROMOTED OWNER
```

`SURVIVOR` означает только выживание на текущем evidence/holdout.

## 7. Competition

`competitor_diversity_target = 5` является поисковой эвристикой, а не логическим условием истины.

Если доступно `m<5` независимых кандидатов:

- система не объявляет их ложными;
- фиксирует coverage/underidentification;
- может продолжить candidate birth или назначить различающий эксперимент.

Scientific Promotion принимает решение по evidence, а не по магическому числу кандидатов.

## 8. Experiment selection

Если есть явные predictive likelihoods, допускается exact EIG владельцем DomainNeutralInformationGainOwner.

Если likelihoods отсутствуют, Atlas не имеет права их придумывать. Adaptive kernel может ранжировать доступные experiment points только по deterministic candidate-disagreement proxy:

```math
V(x)=\operatorname{Var}_h[\hat y_h(x)],
```

что явно маркируется как `NOT_PROBABILISTIC_EIG`.

## 9. Mathematical invention

Если текущий язык не закрывает residual, используется существующий:

```text
PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0
```

с цепочкой:

```text
Φ scan
→ representation obligations
→ generated primitive
→ morphism
→ controlled limit
```

Known representation name не является обязательным входом.

## 10. Executable representation synthesis

При representation gap Atlas может перейти от symbolic obligations к исполнимому candidate только через typed operator-response evidence.

```math
\{\psi^{(q)}\mapsto y^{(q)}\}_{\rm discovery}
\to
\widehat O
\to
\text{freeze}
\to
\{\psi^{(*)}\mapsto y^{(*)}\}_{\rm sealed}
\to
\text{compile}
\to
\text{execute}.
```

Current compilation/experiment contract:

```text
OPERATOR-PROBE-DESIGN/2.1.0
PHI-THEORY-COMPILER/2.0.0
EXECUTABLE-REPRESENTATION-SYNTHESIS/2.0.0
EXECUTABLE-THEORY-RUNTIME/2.0.0
```

Обязательные инварианты:

```text
known_law_name_required = false
generated_source_code = forbidden
sealed_operator_probe_used_for_term_selection = false
missing_probe_values_filled_by_AI = false
compiled_candidate_is_world_law = false
```

Разрешённые executable classes:

```text
EXACT_FINITE_TRANSITION_ALGEBRA
TYPED_CONTINUOUS_OPERATOR_PROGRAM
STANDARD_EIGENPROBLEM
GENERALIZED_EIGENPROBLEM
SELF_CONSISTENT_EIGENPROBLEM
```

Если response probes отсутствуют, Atlas обязан сначала freeze-ить собственный response-free probe-input protocol. Он не имеет права подставить response values. Если current design shell не достигает необходимой идентифицируемости, открывается следующий design shell; глобального probe-count ceiling нет.


### 10.1 Direct representation-gap entry

Representation gap является самостоятельным допустимым входом исследовательского ядра и не требует фиктивной регрессии по выдуманным observations. Для gap-entry требуется attestation:

```math
G=(k, d_G, o_G),\qquad d_G=H(E_G),
```

где `k` — тип gap, `E_G` — capability/residual evidence, `o_G` — provenance. Без `d_G` вызов rejected. Gap evidence не считается operator measurement. При `blind_no_named_law_catalog=true` owner-law catalog не читается.

```math
G + \varnothing_{response}
\longrightarrow
\mathcal P_{freeze}
\longrightarrow
\texttt{REPRESENTATION\_GAP\_OPERATOR\_PROBE\_PROTOCOL\_FROZEN\_AWAITING\_ATTESTED\_RESPONSES}.
```

`\mathcal P_{freeze}` содержит только grid/state/role/probe-id. Только attested пары `state -> operator response`, связанные с frozen `probe_id`, могут открыть последующую ветвь synthesis/compile/execute.

## 11. Claim provenance

Единственный owner для `ATLAS_NATIVE`:

```text
CLAIM-PROVENANCE-FIREWALL/15.2.8
```

Обязательный receipt:

```text
owner = ADAPTIVE-RESEARCH-KERNEL/15.4.0
schema
input_digest
axis_registry_digest
hypothesis_space_digest
code_digest
result_digest
digest
```

Проверяется self-digest execution receipt. При несоответствии:

```text
REJECTED_ATLAS_NATIVE_PROVENANCE
```

## 12. AI boundary

AI-facing `propose_candidate` не может установить:

```text
ATLAS_NATIVE
ESTABLISHED_LAW
CONFIRMED_CONSTANT
EXPERIMENT_PASS
```

Assistant proposal получает origin `ASSISTANT_HYPOTHESIS` и может стать Atlas result только после независимого исполнения ядром.

## 13. Scientific truth

```math
ATLAS\_NATIVE\not\Rightarrow LAW.
```

Scientific truth/promotion требует отдельного Scientific Promotion / Scientific Verification receipt.

## 14. Domain solvers

Adaptive Research Kernel не подменяет domain truth готовым вручную выбранным solver. Он может синтезировать generic executable representation candidate из attested operator probes, но такой candidate остаётся TESTABLE и не становится domain authority до независимой falsification/promotion. Numerical authority остаётся у domain owners. Kernel может:

- выбрать owner-connected region;
- сформировать research question;
- синтезировать hypothesis representation;
- назначить discriminating experiment;
- передать задачу domain solver;
- принять numerical receipt как evidence.

## 15. Atomic benchmark

Atomic frontier — regression benchmark общей архитектуры. Его numerical receipts не определяют universal Research Kernel и не устанавливают общий `Zmax`.

## 15.1 Atomic reference-world interaction

Current typed world owner:

```text
ATOMIC-REFERENCE-WORLD-INTERACTION/1.0.0
```

принимает только frozen response-free Atlas probe protocol. До исполнения обязательно:

```math
\operatorname{digest}(\mathcal P)=d_{\rm freeze},
\qquad
\forall q:\; y^{(q)}=\varnothing.
```

Owner может вернуть `TYPED_CARRIER_REDESIGN_REQUIRED`; после такого feedback новый protocol обязан быть заново порождён Atlas и снова freeze-нут до response acquisition.

При явном `allow_reference_simulation=true` owner возвращает digest-bound operator responses. Evidence обязан содержать:

```text
reference_simulation = true
world_measurement = false
answer_bearing_regression_used = false
atomic_frontier_module_used = false
oracle_visible_before_probe_freeze = false
```

Reference-world coefficients или solver identity не передаются в hypothesis/synthesis input. Они могут быть раскрыты только в post-freeze audit. Полученный executable candidate имеет статус `TESTABLE/NOT_LAW`; successful reference control не может установить физический `Zmax`, завершить periodic-table genesis или считаться empirical verification.

## 16. Regression isolation and API completeness

Public `LawSpaceAPI` состоит из трёх непересекающихся registries: `READ_TOOLS`, `MUTATION_TOOLS`, `REGRESSION_TOOLS`. Любой public method должен быть классифицирован ровно один раз.

Для blind/default исследования действует

```math
\mathcal T_{blind}\cap\mathcal T_{regression}=\varnothing.
```

Answer-bearing atomic/high-Z/post-freeze owners не удаляются, но доступны только при явном `regression_mode=True`. Отсутствие opt-in обязано завершаться fail-closed до чтения regression receipt.

## 17. Release integrity

Controlled code/data/configuration files имеют hash ledger. Все immutable report/evidence files также входят в manifest ledger `(path,size,sha256)`. Current replay outputs могут изменяться только если путь входит в фиксированный mutable-report whitelist; их смысловые результаты отдельно bindятся qualification digest-ами в manifest.

Следовательно, изменение historical evidence без reseal или добавление нового mutable report path без rebuild является нарушением release contract.

## 18. External knowledge

External references должны иметь `EXTERNAL_REFERENCE`. Они не могут быть перекрашены в `ATLAS_NATIVE`.

Для blind/freeze эксперимента внешние данные допускаются только в явно определённой стадии protocol; current 15.2.8 energy-space + temperature-axis control вообще не использует интернет.


## 15.2 Variable-particle / self-consistent world interaction

Current additional owners:

```text
VARIABLE-PARTICLE-PROBE-DESIGN/1.0.0
ATOMIC-VARIABLE-PARTICLE-REFERENCE-WORLD/1.0.0
SELF-CONSISTENT-REPRESENTATION-SYNTHESIS/1.0.0
```

The occupancy design is an experimental coordinate design, not an object-existence claim. Atlas freezes a set of integer occupancy coordinates before response acquisition and must not interpret the largest probed count as a physical upper index.

For frozen state `psi`, normalized density `rho`, particle coordinate `N` and a typed field response `F`, the generic self-consistent synthesis gate searches an extension

```math
\mathcal O_{\mathrm{sc}}[F]\psi
=
\mathcal O_0\psi
+
\sum_{a,b} g_{ab}F\,\psi_b,
```

and an affine-occupancy elliptic field update

```math
(-\partial_x^2+\lambda I)F
=
(aN+b)\rho.
```

The coefficients `g_ab`, `lambda`, `a`, and `b` are inferred from discovery rows only and must pass a sealed holdout that was frozen before the reference-world responses. The executable lowering is `SELF_CONSISTENT_EIGENPROBLEM`; runtime occupancy may be varied through the typed runtime request without recompiling the operator grammar.

A passing reference-simulation cycle establishes only that Atlas can synthesize and execute a variable-particle fixed-point representation from hidden black-box responses. It does **not** establish physical atom existence, nuclear binding, decay stability, chemistry, a periodic-table continuation, or a physical upper `Z`.

- The active periodic frontier MUST NOT contain a numeric terminal `Z` or iteration/visit ceiling. The physical scan stops only at a typed evidence/representation/falsification gate. Electronic outputs beyond the closed prefix MUST be set-valued under unresolved identifiability; relativistic `Zalpha` is active, channels may be born adaptively, mixtures are allowed, and symbolic candidate spaces must not be mistaken for physical element existence.

## Open-ended nuclear object-existence contract

Authoritative owner: `NUCLEAR-BINDING-DECAY-WORLD-INTERACTION/1.0.0`.

- `fixed_upper_Z = null`; `fixed_upper_N = null`; numeric visit ceiling = null.
- Physical table advance requires independently attested Z identity and a non-estimated nuclide lifetime `>= 1e-14 s`.
- Absence of an attested nuclide is `UNKNOWN`, never a non-existence proof.
- `OPEN_ENDED_GROSS_SEMF_BA_OPTIMIZATION/2.0`, VSS and UDL outputs are reference simulation evidence only.
- Gross SEMF may not establish shell closure, an island of stability, or physical `Zmax`.
- Alpha partial half-life may not be relabelled total half-life.
- Until spontaneous-fission barrier/action and competing beta/EC rates are identified, `total_half_life = UNKNOWN` and `physical_Zmax = UNKNOWN`.
- Reference simulation is not an empirical world owner and cannot promote an element.


## Electronic state-space contract — release 15.4.0

Authoritative domain owner: `ELECTRONIC-STATE-SPACE-SEARCH/1.1.0`.

Required invariants:

```text
configuration_table_used_as_answer = false
element_exception_dictionary_used = false
madelung_aufbau_used_as_answer = false
published_configuration_order_used = false
fixed_upper_Z = null
fixed_upper_n = null
fixed_upper_l = null
fixed_candidate_count_as_truth_gate = false
unstable_representation_ranking_returns_unknown = true
```

`atomic_dirac_evaluator` owns only radial eigenproblem evaluation. `atomic_scf_evaluator` owns only evaluation of caller-supplied occupations and explicit nuclear hypotheses. Configuration birth/competition belongs only to the electronic state-space owner. A numerical grid/iteration limit is an execution-resolution parameter, not a scientific search-space boundary.

A finite nuclear radius must carry provenance. A reference nuclear model may be used as a hypothesis source but may not be relabelled empirical evidence. A candidate minimum is never promoted directly to scientific truth.


## Evidence-born many-body operator-coordinate contract — release 15.4.0

Authoritative orchestration owner: `ADAPTIVE-RESEARCH-KERNEL/15.4.0`. Theory kernel: `PHI-THEORY-COMPILER/2.1.0`.

Required owners:

```text
MANY-BODY-OPERATOR-PROBE-DESIGN/1.0.0
ATOMIC-MANY-BODY-REFERENCE-WORLD/1.0.0
MANY-BODY-OPERATOR-COORDINATE-SYNTHESIS/1.0.0
```

Required invariants:

```text
known_many_body_method_required = false
named_solver_selection = false
fixed_global_interaction_rank_ceiling = null
probe_inputs_frozen_before_world_response = true
sealed_holdout_used_for_coordinate_selection_only_after discovery fit = true
reference_simulation_is_empirical_world = false
coulomb_kernel_exposed_to_synthesis = false
known_ground_state_configuration_used = false
blind_rank_precommitted_before_blind_response = true
blind_rank_may_adapt_after_holdout = false
precommitted_rank_validation_relabels_rank_as_minimum = false
finite_carrier_is_physical_basis_completeness_claim = false
```

For fixed `N,M`, interaction shells are generated from number-conserving normal-ordered fermion monomials. A shell may be expanded only after a sealed operator-action residual. A discovered `operator_interaction_rank` is research-local and may be promoted to canonical status only through the normal axis-lifecycle procedure.

The current `Z=1 -> Z=2 -> blind Z=3,4` experiment is a release qualification on an independent deterministic reference simulation. It MUST NOT be relabelled a physical proof that atomic interactions have universal rank 2, a complete correlation representation, a physical ground-state solver, or a named CI/MCDHF implementation.

## Transactional current-replay contract — release 15.6.1

- Current test inventory is dynamically collected and frozen before replay execution.
- Partitioning into fresh-process batches is runtime isolation only; it may not delete, skip, rewrite, or weaken any collected node.
- Aggregate PASS requires the post-execution collected inventory to equal the frozen inventory exactly, every batch receipt to bind the same plan digest, and every node to PASS.
- `max_nodes_per_surface` and execution timeout are not scientific search ceilings and may not be interpreted as limits on axes, hypotheses, interaction rank, atomic Z/N, or physical truth.

## Persistent Law Atlas contract — release 15.6.1

Authoritative owner: `ATLAS-LAW-SPACE-SEARCH/1.0.0`.

Compatibility only: `SCIENTIFIC-AXIS-SPACE/1.0.0`.

Required invariants:

- the primary scientific object is the persistent typed axis/parameter Atlas, not an expression tree;
- canonical axes are append-only/reusable at the registry level; a dormant axis is not deleted or forgotten;
- benchmark/domain adapters may bind observable labels to typed descriptors but may not own target laws;
- `ATLAS-LAW-SPACE-SEARCH` contains no benchmark-variable dictionary and receives no hidden target expression;
- known-law catalogue is not required;
- fixed global scientific-axis ceiling is `null`;
- reusable state/geometry/thermal/phase/relativistic/coherence/response coordinate archetypes live in canonical domain registries rather than a Feynman-local solver;
- novel coordinate proposals route through `DYNAMIC-AXIS-ADMISSION/6.24.0` and `DYNAMIC-AXIS-PROMOTION/8.0.0`;
- relation hypotheses route through `SCIENTIFIC-PROMOTION-CORE/9.0.0` and are not auto-promoted to laws;
- owner-connected higher joint-axis shells may open after residual evidence; an execution shell is not a universal complexity ceiling;
- dimensional/type consistency precedes response activation;
- additive selection is rank-aware and validates the actual residual;
- benchmark target formulas remain evaluation/world data and may not be imported into `source/` as answer-bearing knowledge;


## Post-clean current-state contract — 15.7.0

The release MUST preserve the 15.6.1 cleaned scientific baseline and MUST NOT restore historical generated candidates, evidence, frontiers, ScienceAtlas calculations, particle results, replay batches or generated quantum routes. Exactly one current research result MAY be persisted: `reports/FIRST_POST_CLEAN_ATLAS_EXPERIMENT_CURRENT.json`. Its digest MUST equal a fresh deterministic replay by `evaluation.first_atlas_native_experiment`.

The experiment MUST start with `drive` as the only active predictor and `medium_state` as a dormant observable coordinate. `medium_state` MUST NOT occur in the initial hypothesis formula space. It MAY be activated only after residual-axis evidence. The sealed holdout MUST NOT participate in axis activation. The final controlled-world claim MUST remain `scientific_truth_established=false` even when the execution provenance is `ATLAS_NATIVE`. AI-Feynman-100 remains absent.


## Blind real-scientific experiment contract — 15.8.0

1. Discovery MUST NOT consume the independent flexible-mode descriptor before freeze.
2. OOD regime MUST be `U=40m/s`.
3. A born coordinate MUST improve OOD RMSE and survive local multiscale perturbations.
4. Post-freeze reconciliation MUST NOT retroactively alter the frozen discovery digest.
5. Coincidence with an existing physical coordinate MUST be reported as rediscovery, not novelty.
6. This receipt MUST NOT mutate the canonical axis registry or establish a world law.



## Historical Atlas-wide frontier candidate contract — sealed 15.9.0

Authoritative search mathematics remains owned by the existing domain/frontier owners. `evaluation.lawspace_qualification.run_frontier_scan_current` is orchestration and ledger materialization only; it MUST NOT introduce a second search algorithm or hidden answer-bearing rule.

Historical 15.9.0 invariants (retained for provenance; superseded for current cardinalities/search termination by 15.10.1):

1. Baseline mutable registries remain `candidates=0`, `evidence=0`, `generated quantum routes=0`.
2. Active research candidates are stored separately in `data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl`.
3. Every materialized candidate returned by child owners MUST be persisted in the ledger exactly once by candidate ID.
4. Ranking/top-N views MUST NOT delete, demote to false, or remove a candidate from the complete ledger.
5. `known overlap`, `partially explained`, `prior-art review required`, `current-corpus unmaterialized`, and `novelty unresolved` are epistemic annotations; none is a deletion rule.
6. Current-corpus absence MUST NOT be promoted to world-science novelty.
7. A scanned cross-domain pair that is not materialized in the attention view remains `ADDRESSABLE_OPEN_REGION_NOT_FALSIFIED_NOT_REJECTED`.
8. The sealed 15.9.0 `256` pair materialization count and total `429` ledger count are historical release-execution facts, not scientific ceilings and not current 15.10.1 cardinalities.
9. An execution budget stop in algebraic elimination MUST be reported as an open execution frontier and MUST NOT be interpreted as source-order exhaustion or a universal complexity ceiling.
10. Domain labels MUST NOT be used as pre-search gates. A candidate may remain cross-domain until evidence supports a narrower interpretation.
11. The provisional `gust_probe_to_wing_transfer_magnitude` coordinate MUST NOT mutate the canonical axis registry without the normal axis-lifecycle promotion procedure.
12. The five DLR real-data mechanism hypotheses MUST remain present while `unique_mechanism_identified=false`, irrespective of posterior ranking.
13. A full frontier owner that does not complete MAY remain explicitly open; a reduced/truncated substitute MUST NOT be relabelled a complete scan.
14. The existing probe-to-wing discriminator owner MUST be executed before declaring the proposed discriminator complete. Synthetic/mechanism qualification MAY certify the method, but a real causal/mechanism update MUST remain blocked unless synchronized upstream and near-wing gust channels, complex load phase, at least two speeds, and independent same-test modal records satisfy the owner contract.
15. Partial public magnitude evidence MUST NOT be converted into `G_probe_to_wing` by a model-derived near-wing channel, cross-campaign modal splice, phase fabrication or posterior update. Missing required measurements produce `CANDIDATE_REAL_DATA_PENDING`, not falsification.
16. `new_scientific_law_established_by_scan=false` for this release.

For the sealed 15.9.0 execution the ledger cardinality is

```math
256+156+11+5+1=429.
```

This equality is a deterministic release qualification target only. It does not constrain future candidate birth.




## Atlas-wide frontier candidate contract — CURRENT 15.10.1

The authoritative active frontier is regenerated from the existing owners and stored in `data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl`. Current invariants are:

1. Baseline mutable candidate/evidence/generated-route registries remain clean; historical `2771` controls are provenance only.
2. Every materialized current candidate is persisted exactly once by content-addressed ID and remains active until a declared falsification/promotion transition.
3. Current materialized cardinality is

```math
256+6+116+11+5+1=395,
```

corresponding respectively to pair, owner-connected higher-order, algebraic-basis, operator, real-data mechanism and provisional-axis records. This is a release execution fact, not a universal bound.
4. Pair scan covers all `183,996` pairs in the current 655-axis snapshot; the 256 materialized pair records are an attention/materialization view. Non-materialized pairs remain addressable and not falsified.
5. Higher-order exploration MUST use owner-connected directed research. No fixed tuple-order witness list, fixed axis-order ceiling or fixed owner-visit scientific ceiling may determine reachability. Current execution materializes 6 connected regions and reaches active axis order 324.
6. Algebraic polynomial search MUST terminate by mathematical saturation/fixpoint of each connected current-source ideal, not by a fixed resultant/evaluation/frontier-state budget. Current source set: 18 relations, 3 components, 116 canonical Gröbner-basis consequences, maximum connected source order 16. `ALGEBRAIC_IDEAL_BASIS_SATURATED` closes only those current polynomial ideals.
7. Operator search terminates only at `FRONTIER_EXHAUSTED` for the current typed operator frontier and carries `fixed_execution_visit_ceiling=null`.
8. Known overlap, partial explanation, current-corpus absence and novelty-unresolved are epistemic annotations, never deletion rules.
9. `UNKNOWN/GAP` is mandatory whenever evidence, representation or discriminating measurement is absent.
10. Qualification/orchestration code may materialize receipts and ledgers but MUST NOT become a second scientific solver.

## Low-frequency gust anomaly contract — 15.10.1

Authoritative owner: existing `ConstraintAtlasOwner`; no parallel solver is introduced.

The public-evidence analysis SHALL compute Figure-16 residuals exactly from the preserved vector-digitized dataset and SHALL mark the derived

\[
|G_{\rm eff}|=10^{-(M_{sim}-M_{exp})/20}
\]

as conditional rather than measured. The 4–8 Hz mean residual MUST reproduce `1.7612432509816798 dB` within numerical precision and the mean conditional amplitude ratio MUST reproduce `0.8165672757732683`.

The multi-speed scalar-gain test SHALL normalize each open-loop spectrum to its own 9 Hz sample before comparing spectral shape. Any lack of a published digitization uncertainty model SHALL prevent formal falsification from this test alone.

The flap→WRBM path SHALL remain a negative control only; it SHALL NOT be treated as proof that H005 is false.

The next discriminator SHALL preserve the three independent physical states `NO_WING`, `RIGID_WING`, `FLEXIBLE_WING` and require synchronized complex upstream/encounter gust signals, WRBM and modal measurements. Missing real channels SHALL produce `DATA_PENDING`, never synthetic substitution.

Generic candidate lifecycle, novelty and falsification rules SHALL continue to delegate to `COMMON-SCIENTIFIC-RULES/1.0.0`.


## Integration/replay/seal contract — 15.10.1

1. Historical control snapshots SHALL NOT be counted as active candidate records.
2. Joint qualification SHALL invoke current authoritative owners directly and SHALL NOT depend on deleted historical report receipts.
3. Canonical replay digests SHALL exclude volatile timing/stdout text while preserving it as diagnostic evidence.
4. Seal acceptance requires exact closed-world file-set equality.
5. UNKNOWN / novelty-unresolved candidates SHALL remain active until evidence resolves them; archival cleanup SHALL NOT imply falsification.


## Resident cognitive / AI contract — inherited 15.10.2 foundation

1. The AI capability ledger MUST be derived from current executable owners/APIs/registries/qualifications and MUST NOT require a deleted historical capability snapshot.
2. Cognitive and resident mutable state MUST resolve outside the sealed release root by default.
3. Resident learning MAY modify memory, concepts, goals, plans, skills, composed operators and world-action models; it MUST NOT directly assign scientific truth or mutate canonical scientific axes without the authoritative scientific owner/gate.
4. World-action models MUST be learned from admitted post-freeze experiences. Prefreeze truth leakage, caller-supplied benchmark likelihood tables and unsupported OOD extrapolation are forbidden.
5. Concept promotion, operator qualification and reflexive/developmental transitions MUST remain proof/evidence carrying and fail closed when their gates are absent.
6. Autonomous research MUST report an explicit GAP/next required external input when independent evidence is unavailable. Missing evidence MUST NOT be synthesized.
7. `consciousness_claimed=false` and `agi_claimed=false` are release invariants. A resident heartbeat or self-model is not evidence of either.
8. The external wake state is a mutable runtime artifact, not part of the sealed scientific distribution and not a prerequisite for reproducing scientific qualification.
9. Current unresolved architecture obligation `COLLECTIVE_COORDINATION` MUST remain visible until an owner-qualified implementation closes it.

## 15.10.2 AI acceptance orchestration contract

1. Every cognitive owner keeps exactly one authoritative qualification surface.
2. Full owner acceptance is executed independently; `joint_qualification` MUST NOT recompute the same heavy owner workload as an integration side effect.
3. Joint MUST execute a live Cognitive Core → Resident path plus an actual QPDTR-neutrino binding and MUST verify the remaining accepted qualification surfaces are callable.
4. Mutable resident state MUST resolve outside the sealed release tree.
5. Resident learning MUST NOT mutate canonical scientific axes, release-controlled source evidence, or promote a scientific candidate by itself.
6. A fail-closed evidence request (`*_INDEPENDENT_EVIDENCE_REQUIRED`, `BLOCKED_NO_ADMISSIBLE_PROSPECTIVE_MEASUREMENT`, or equivalent) is a valid epistemic outcome and MUST NOT be converted into a fabricated PASS-world result.


## Adaptive multidimensional subspace contract — CURRENT 15.11.0

The existing `CandidateGenerationPipeline` is the single authoritative frontier owner for adaptive local scientific-subspace navigation. No parallel explorer/solver is introduced.

For the canonical axis set `A`, admissible local hypothesis regions have arbitrary finite order `k>=2`; `fixed_subspace_order_ceiling = null`. All registered axes are addressable, but `all_axes_used_simultaneously_by_default = false`.

Higher-order nomination MUST NOT require prior success of every lower-order projection. The current structural nomination sources are exact pair frontier, owner co-binding, typed bridge motifs, bridge-connected owner merges and semantic/role higher-order motifs. Unmaterialized regions remain open/unrejected.

Every materialized adaptive candidate MUST contain: exact axis membership/order; nomination provenance; owner/domain/role structure; problem/research-question contract; applicability/GAP contract; competing mechanism families; a discriminating-experiment blueprint; and explicit claim boundaries. Candidate ranking/importance is routing metadata and MUST NOT be treated as evidence.

Before scientific promotion, the ordinary evidence gates apply. Where relevant the candidate experiment MUST include whole-pipeline permutation/null calibration, convention/unit controls, lower-order controls, non-overlapping regime/OOD holdout and independent world attestation.

`NOT_FOUND_IN_LITERATURE` is neutral and MUST NOT map to falsification or deletion. `KNOWN_OVERLAP` also MUST NOT imply deletion; overlap is an epistemic/prior-art label.

Current execution materialized 1,005 adaptive candidates from 378 structural seeds, orders 3...37, within a 1,394-record active ledger. These counts and observed orders are execution state, not scientific limits.


## Post-freeze prior-art contract — CURRENT 15.11.0

Let `L_f` be the frozen active candidate ledger with digest `d_f`. Any literature/prior-art receipt `P` is admissible only if `P.bound_active_candidate_ledger_sha256 = d_f` and every reviewed candidate ID already exists in `L_f`. Literature is forbidden as a pre-freeze nomination signal for this receipt. Allowed classifications include `KNOWN_OVERLAP`, `PARTIAL_OVERLAP`, and `NOVELTY_UNRESOLVED_*`.

The following implications are forbidden:

`NOT_FOUND_IN_SEARCH(c) => FALSE(c)`

`NOT_FOUND_IN_SEARCH(c) => NOVEL_LAW(c)`

`KNOWN_OVERLAP(c) => DELETE(c)`

Prior-art review is metadata for research routing. Scientific promotion still requires discriminating evidence and authoritative owner gates. The current receipt is bound to ledger SHA-256 `5bc30ce9a7291f49cebf78021b538c1e558e1ce97f629f6d63310f6eaa20541f`.


## Core Convergence contract — CURRENT 15.12.0

- Canonical dimensional basis: `L,M,T,I,Theta,N,J`.
- Law-space dimension arithmetic: exact rational rank/RREF/nullspace via the existing `phi_compiler_owner` authority.
- A five-component descriptor is compatibility input only; it is normalized before internal search and is reported as legacy padding.
- Adaptive higher-order nomination remains independent of successful lower-order projections.
- Exact fit or dimensional admissibility never auto-promotes a law.
- Convention audit, source-law derivability, OOD/regime evidence, cross-system transfer and whole-pipeline permutation null remain promotion gates when applicable.
- Whole-pipeline permutation null is required before scientific promotion, not before every raw coordinate nomination.
- No parallel symbolic-regression core is introduced.


## Qualification Runtime Convergence contract — CURRENT 15.13.0

The authoritative promotion implementation SHALL remain `SCIENTIFIC-PROMOTION-CORE/9.0.0`; no second active law-promotion owner is permitted.

Every candidate persisted by the current Atlas frontier materialization SHALL carry exactly one valid `phi-frontier-promotion-path/v1` receipt with the ordered gates:

```text
U0_RECORD_INTEGRITY
U1_TYPED_HYPOTHESIS_BINDING
U2_EXACT_DIMENSIONAL_QUALIFICATION
U3_CONVENTION_ARTIFACT_AUDIT
U4_KNOWN_DERIVABILITY_AUDIT
U5_COLLAPSE_OR_INVARIANCE
U6_DISTINCT_REGIME_OOD
U7_CROSS_SYSTEM_REPLICATION
U8_WHOLE_PIPELINE_PERMUTATION_NULL
U9_DISCRIMINATING_EXPERIMENT
U10_NUMERIC_PROMOTION_CORE
```

A missing evidence packet SHALL yield a pending gate and SHALL NOT set the candidate false. A source-derived consequence SHALL remain a retained research object but SHALL NOT be promoted as an independent new law. A provisional research axis SHALL delegate to the existing Dynamic Axis Promotion route.

`U8_WHOLE_PIPELINE_PERMUTATION_NULL` SHALL require a null distribution generated by the declared complete adaptive proposer/selector pipeline, with an explicit trusted evidence owner, method, evidence digest and pipeline digest. The current default SHALL require at least 200 null runs and empirical one-sided p-value `<= 0.01`. A post-selected single-model null SHALL NOT satisfy this contract.

The old numeric scientific-promotion call SHALL NOT be a bypass. `LAW_CANDIDATE` requires a valid prepromotion-ready unified receipt that is itself content-addressed inside the request's scientific-verification artifact set and whose candidate identity matches the request. Without that receipt, the numeric path SHALL NOT emit `LAW_CANDIDATE` even when its older numeric/world gates pass.

The API method `qualify_frontier_promotion_path(record, controls=None)` SHALL delegate to the same Scientific Promotion Core authority. Future materialized subspaces SHALL use this same runtime rather than defining domain-specific promotion shortcuts.

A promotion-path receipt is a process/evidence-routing certificate, not empirical evidence and not a scientific truth assignment.

## Fair Open-Ended Dovetail contract — CURRENT 15.14.0

1. `CandidateGenerationPipeline/6.25.0` remains the single authoritative adaptive frontier owner; no second explorer SHALL be active.
2. The 15.13 active candidate ledger and all 1,005 adaptive frontier records SHALL be preserved as the initial materialized state. Dovetail continuation SHALL NOT rewrite those records merely to attach scheduling metadata.
3. Axis birth order SHALL be append-only. Existing birth ranks SHALL NOT be renumbered when new axes appear.
4. Pair coverage SHALL use diagonal enumeration by maximum append-only birth rank. There SHALL be no fixed pair-seed ceiling.
5. Node coverage SHALL use finite round snapshots. Nodes born during a round SHALL enter a later round rather than extending the current round indefinitely. There SHALL be no fixed node-visit ceiling.
6. Every materialized node SHALL carry persistent address progress and a local scientific-search shell. Repeated node visits SHALL advance local search depth; `fixed_maximum_shell = null`.
7. Shell 0 SHALL preserve the 15.13 local search envelope. Positive shells MAY increase support/exponent/feature/sparse-term budgets, but these budgets SHALL be interpreted only as finite execution budgets for that shell.
8. Structural importance/ranking SHALL NOT gate the fair coverage lane. A low-ranked missing-axis edge remains addressable.
9. The sealed release SHALL contain a digest-valid dovetail snapshot. Mutable traversal advancement SHALL resolve outside the sealed tree and SHALL NOT modify the sealed snapshot.
10. Environment rebasing MAY append newly born axes and requalify nodes, but SHALL preserve old nodes/progress. `old_nodes_deleted=true` is forbidden.
11. A finite execution tranche SHALL NOT be interpreted as exhaustion of the scientific space. An unvisited address SHALL remain `UNKNOWN`, never `FALSE`.
12. The fair-traversal guarantee is conditional on unbounded repeated advancement. For each finite subset whose members have finite append-only birth ranks, the scheduler SHALL provide a finite address path.
13. Scientific promotion remains exclusively under the 15.13 unified `U0...U10` runtime; traversal/materialization alone SHALL NOT establish a law.



## Knowledge-Binding / Hypothesis-Materialization contract — CURRENT 15.15.0

1. `LawCatalog` remains the single canonical passport/owner catalog; owner-axis bindings are a qualified overlay loaded from the existing Knowledge Evolution state.
2. A production owner-axis binding MUST reference an existing owner, an existing same-domain canonical axis, the exact owner digest, and at least one internal semantic witness from scientific coordinate, formula, assumption or observable.
3. A binding MUST NOT be interpreted as a new law, world measurement, novelty result or cross-domain bridge.
4. Missing or unqualified bindings MUST remain `PENDING`; name similarity alone cannot create a binding.
5. The sealed 15.15 dovetail snapshot MUST preserve the 1,005 legacy adaptive baseline IDs and the 2,175 continuation nodes; environment requalification may add nodes but MUST NOT delete legacy ones.
6. The active 15.15 ledger MUST preserve every candidate ID present in sealed 15.14. Enriched payloads from qualified re-evaluation are permitted and provenance-visible.
7. `ScientificPromotionCore/9.1.0` remains the one promotion authority. A typed relational materialization freezes axes, owners, null/alternative families and measurement contract; it MUST NOT invent a scalar equation, coefficient, measurement or novelty claim.
8. A valid relational materialization may satisfy U2/U3 only by explicit non-applicability to a non-scalar relation; it MUST NOT skip U4 derivability or empirical U5–U10.
9. Every persisted materialization MUST be content-addressed and bound to both `candidate_id` and `candidate_core_digest`.
10. Missing evidence at U4–U10 keeps the candidate active and pending; it MUST NOT mark the candidate false.
11. Candidate-count growth is not an acceptance criterion; executable depth through unified gates is.


## P2 Closure / Scientific Audit Depth contract — CURRENT 15.16.0

1. Conservation-invariant discovery SHALL return an equivalence class under admissible monotone reparameterization and trajectory-constant scaling; it SHALL NOT choose a canonical physical representative from constancy alone.
2. Canonicalization SHALL require an explicit independent composition/extensivity law. In its absence the gate SHALL fail closed.
3. The integrated version identity SHALL be the vector `(SYSTEM_RELEASE, COMPONENT_SCHEMA_VERSION, STATE_SCHEMA_VERSION, AI_ACCEPTANCE_VERSION)`; these coordinates SHALL NOT be collapsed into one scalar release identifier.
4. Resident snapshot restore SHALL verify both raw-byte SHA-256 and internal state digest before migration. Supported schema migration SHALL be pure with respect to scientific evidence and SHALL report `scientific_truth_changed=false`.
5. Resident restore SHALL commit atomically only to an external validated state path; overwrite requires explicit authorization.
6. `audit-read-only` SHALL snapshot the complete sealed tree before and after current-state, joint and seal qualification with bytecode disabled and runtime state externalized. Any file/directory/symlink mutation SHALL fail the audit.
7. `ScientificPromotionCore/9.2.0` remains the one promotion authority. A materialized relational hypothesis may pass U4 only through a digest-bound formal alternative-derivability audit against accepted source owners.
8. U4 `PASS_NOT_DERIVED_FROM_ACCEPTED_LAWS` means only that source-owner acceptance does not logically force the selected joint interaction. It SHALL NOT be interpreted as empirical support, literature novelty or a new law.
9. U5 requires admissible measured collapse/invariance evidence. Missing world evidence SHALL keep U5–U10 pending.
10. The frozen 254-hypothesis population SHALL remain fixed for this depth audit; no post-hoc replacement by easier candidates is allowed.
11. Automatic scientific promotion from P2 closure, version migration, read-only audit, or U4 formal audit is forbidden.


# 15.17.0 — SCIENTIFIC EXPLOITATION / AI RESEARCH LOOP INTEGRATION

## Цель релиза

15.17.0 переводит 254 материализованные гипотезы, прошедшие U4, из состояния «известен следующий gate» в состояние полного исполняемого evidence-acquisition portfolio U5–U10. Релиз не подменяет отсутствующие world measurements синтетикой и не объявляет новые законы.

## Исполняемая цепь

Для каждого кандидата строится digest-bound dossier

```math
D_c=(U5,U6,U7,U8,U9,U10),
```

где U5 требует измеренного collapse/invariance evidence; U6 — отдельного OOD regime; U7 — независимой replication system/source; U8 — whole-pipeline permutation null; U9 — prospective discriminating experiment; U10 остаётся исключительным authority ScientificPromotionCore.

Текущий census: 254/254 dossier построены, из них 186 single-domain и 68 cross-domain. World evidence внутри sealed release отсутствует, поэтому U5=U6=...=U10=0 и это является корректным PENDING_EVIDENCE, а не отрицанием кандидата.

## ScienceAtlas AI extension 0.9.0

В release включён проверенный исследовательский исполнитель `extensions/ATLAS_AI_RESEARCH_EXTENSION_v0_9_0`. Его разрешённая роль: prospective closed research loop, operator genesis, regional meta-learning, lifetime alpha ledger, persistence/rehydration и revocation. Синтезированный оператор является декларативными данными, а не сгенерированным Python-кодом. Whole-pipeline null повторяет enumeration + selection.

AI-extension не получает scientific-promotion authority. Для single-domain dossiers он может выполнять prospective loop напрямую; cross-domain dossier сначала обязан пройти Atlas typed-bridge semantics, после чего AI может работать только с типизированными domain projections.

## Claim boundary

Fixture/synthetic measurement никогда не является world evidence и не может продвинуть U5–U10. Наличие полностью подготовленного dossier не означает наличие подтверждения. Отсутствие world-data не означает FALSE. Open-ended dovetail остаётся активным и не удаляет старый frontier.


## Genesis / lifetime-alpha contract — 15.18.0

1. There SHALL be no fixed terminal genesis shell and no fixed alpha-balance ceiling. Every executed shell SHALL remain finite and deterministically replayable.
2. Evidence alpha SHALL be credited at most once per persistent evidence fingerprint across calls, sample aliases and state restoration. A scoped scientific grant without a stable evidence fingerprint SHALL fail closed; `sample_id` alone SHALL NOT mint scientific alpha.
3. Every credit SHALL carry domain and measured-axis support. A search SHALL spend only compatible credits covering its target and all input axes.
4. Spending SHALL reduce the underlying evidence credits globally; cross-context double spending of one observation is forbidden.
5. Search novelty SHALL be decided before debit. Duplicate searches SHALL be journalled and SHALL consume zero alpha.
6. A strict shell extension on the same split SHALL pay only the previously unpaid family increment; a genuinely new split SHALL pay full search price.
7. Search debit SHALL occur before candidate enumeration and regardless of scientific outcome once affordability and novelty admit execution.
8. A certificate without a bound alpha-spend receipt SHALL NOT be promotable by `GenesisState`.
9. Atomic-term materialisation SHALL be bounded before complete grammar materialisation and SHALL preserve the canonical prefix.
10. Split-local family exclusion SHALL retain an explicit reason and SHALL NOT be silently interpreted as global scientific falsification.
11. The authoritative version vector for this release is `(15.18.0, 6.0.0, 5, 15.10.3)`; these coordinates remain distinct.


## Autonomous epoch Genesis contract — 15.19.0

1. The authoritative acquisition identity remains the sealed 15.18 `ResearchLoopOwner._acquire` boundary; epoch orchestration may not mint a second evidence identity.
2. A scoped ledger may exist transiently as `SCOPED_UNBOUND`, but any grant before binding a fingerprint source fails closed.
3. Scientific acceptance must never silently fall back to an unscoped ledger.
4. A shell decision precedes confirmation acquisition; assessment rows used in the decision are never admitted to that search's FIT/SEAL data.
5. Every confirmation epoch is used by exactly one search and has a unique split digest and disjoint sample set.
6. `PipelineNullCalibrationOwner` uses exact finite-permutation p-values; unresolved finite resolution yields `INSUFFICIENT_NULL_RESOLUTION`.
7. The temporary sequential controller uses exact rational levels and a summable per-target schedule; compute ceilings are not part of the statistical proof.
8. `DEFERRED_RESOURCE` is a scheduler state, not an epistemic rejection and not a scientific search ceiling.
9. Statistical null level, search charge and promotion charge are distinct quantities.
10. Revoked synthesized owners remain historical bus objects but are excluded from incumbent evaluation.
11. The sequential permutation owner is not anytime-valid and does not claim global online FDR control.
12. The authoritative version vector is `(15.19.0, 6.0.0, 5, 15.10.4)`; these coordinates remain distinct.

## Identity/evidence repair contract — 15.19.1

1. System release is `15.19.1`; `AI_ACCEPTANCE_VERSION` remains `15.10.4`.
2. `scienceatlas-ai` distribution/component identity is `0.9.0` consistently across directory, `pyproject.toml`, wheel METADATA, runtime package identity and integration manifest.
3. 0.7.0 serialized AI states remain admissible for migration; new state emission uses 0.9.0 identity.
4. A 15.19.1 acceptance receipt MUST NOT interpret the autonomous `DEFERRED_RESOURCE` fixture as exact blind-law recovery.
5. Machine-readable release evidence MUST include the U0–U10 census and 254-dossier census.
6. Prior exact blind recovery under the superseded N=8 permutation null is not current claim evidence; the reason MUST be recorded explicitly.
7. Replay node inventory remains unchanged from 15.19.0; changed package/evidence bytes MUST produce new replay plan/surface/aggregate identities.


## 15.20.0 permutation e-process contract

1. A permutation orbit MUST be evaluated against one frozen `GenesisJournal` snapshot.
2. Orbit scoring MUST set `journal_write=False`; mutation of either live or frozen journal invalidates the epoch.
3. The permutation group and score rule MUST be fixed before the fresh epoch.
4. Confirmation sample IDs MUST be fresh for the target; reuse fails closed.
5. Exact complete-group normalization MUST satisfy orbit-average e = 1.
6. `E>=1/alpha` is a per-target evidence crossing only. It MUST NOT be interpreted as Atlas-wide FWER/FDR control.
7. No e-process crossing may directly promote a scientific law before a qualified global online controller exists.
8. S6 fixtures selected after orbit inspection are resolution demonstrations only and MUST be labelled as such.
9. Empirical Type-I calibration is executable regression evidence, not a substitute for the conditional e-validity proof.

## 15.21.0 coverage/void contract

1. `CandidateGenerationPipeline` SHALL remain the single authoritative generic frontier generator; no parallel coverage scanner may own scientific candidate truth.
2. Every currently registered canonical axis SHALL be materialized in at least one adaptive candidate after the finite-release coverage pass, but this SHALL NOT be interpreted as pair/triple/higher-order exhaustion.
3. `fixed_axis_order_ceiling`, `fixed_global_step_ceiling`, `fixed_pair_seed_ceiling` and `fixed_node_visit_ceiling` SHALL remain `null`.
4. Every adaptive multidimensional candidate SHALL persist an explicit competing-hypothesis set and a discriminating-experiment contract.
5. Structural coverage witnesses SHALL NOT be counted as earned historical visitation when computing the replay-stable least-visited routing statistic.
6. Research-local axis proposals SHALL be persisted centrally, with provenance and lifecycle status, but SHALL NOT enter the canonical registry unless `DYNAMIC-AXIS-PROMOTION/8.0.0` gates pass.
7. Missing world evidence, unvisited subspaces, and absence of exact prior-art matches SHALL remain `UNKNOWN/PENDING`, never automatic falsification.
8. Every U4-surviving current materialization SHALL have a U5–U10 evidence-acquisition dossier; no dossier is itself world evidence or promotion.
9. Current 15.21 census SHALL be bound to the active ledger: 4106 records, 3706 adaptive spaces, 25942 explicit competing hypotheses, 447 U4 survivors, zero U5+ passes and zero automatic law promotions.



## 15.21.0 exact data-binding contract

10. `SCIENTIFIC-DATA-INGESTION` SHALL expose field-level observables through exact canonical `quantity_id` values and digest-bound selectors; artifact-level provenance alone SHALL NOT count as candidate measurement binding.
11. `CANDIDATE-WORLD-BINDING` SHALL require exact candidate/hypothesis/ExperimentDataIR digests, exact candidate-axis coverage by dataset-compatible owners, exact provenance source-family overlap, exact `quantity_id` overlap and a frozen measurement protocol. Fuzzy label matching SHALL remain forbidden.
12. Dataset compatibility SHALL NOT create `world_measurement_established`, U5 PASS, novelty, or a new-law claim.
13. A dataset-compatible candidate SHALL remain non-executable until a nonempty response-observable projection is frozen against the ExperimentDataIR. Post-hoc response selection SHALL NOT be admissible as confirmatory evidence.
14. The release SHALL preserve the two diagnostic controls: Daya Bay MUST block `SUBSPACE-00BE16B5890A3309672D` by source-family mismatch; `SUBSPACE-0F7BCAA86B7AFED82840` MUST qualify dataset binding but remain response-projection-pending.
15. `world_attestations=0` SHALL remain valid and required while no WORLD-tier attestation passes. A release MUST NOT insert a blocked or qualification-only measurement merely to make this count nonzero.
16. The stored count `25942 = 7 × 3706` SHALL be interpreted only as fixed mechanism-family enumeration. It SHALL NOT be reported as 25,942 independent discoveries or independent scientific evidence items.


## 15.22.0 response-projection / measurement-execution contract

1. `ExperimentDataIR` MAY declare derived responses only by exact canonical `quantity_id`, exact source owner, exact execution owner and exact operation.
2. A response descriptor MUST NOT contain the observed/derived response value.
3. Candidate→dataset binding MUST pass candidate/hypothesis/IR digest checks, source-family overlap, exact quantity overlap and complete candidate-axis instantiation before a response projection may be frozen.
4. The selected response projection MUST be frozen before execution and MUST bind candidate digest, hypothesis digest, binding receipt digest, IR digest, descriptor digest, input observable IDs/value digests, protocol and controls.
5. Measurement execution MUST refuse a stale IR, stale contract, unsupported executor/operation, invalid projection digest or response already present at precommit.
6. Domain likelihood/formula code remains in its existing domain owner. `CANDIDATE-WORLD-BINDING` orchestrates binding/freeze/receipt persistence only.
7. `measurement_executed=true` and a finite response value MUST NOT imply candidate-specific prediction, scientific discrimination, WORLD attestation, U5 or law promotion.
8. U5 remains fail-closed until a typed candidate mechanism is lowered to a predeclared forward prediction on the frozen response space and the existing Scientific Promotion gates receive qualified evidence.
9. Retrospective execution on a published public dataset is data consumption/reanalysis, not independent prospective world attestation.
10. Release 15.22.0 MUST preserve the active candidate ledger: no candidate/axis generation is permitted as a side effect of this repair.

Current qualified instance:

```text
candidate = SUBSPACE-0F7BCAA86B7AFED82840
projection = DAYABAY-CNP-PROFILE-CHI2
chi2 = 595.1908738041352
ndf = 518
reduced chi2 = 1.149017130896014
candidate_specific_prediction_used = false
scientific_discrimination_executed = false
world_attestation = false
U5 = false
```


## 15.23.0 manual prediction-lowering contract

1. A manual lowering is candidate-specific and MUST declare `scope=ONE_CANDIDATE_ONE_MANUAL_LOWERING_NOT_GENERALIZED`.
2. Candidate, typed-hypothesis, dataset-binding, response-projection and lowering-contract digests MUST match before prediction freeze.
3. Discovery and held-out partitions MUST be disjoint and frozen before reveal.
4. Held-out target counts MUST NOT be used while producing `\widehat y`; held-out parameter/source refit is forbidden.
5. The prediction quantity, forward owner, axis→forward-role mapping, nuisance freeze, uncertainty statistic and collapse threshold MUST be declared in the precommit.
6. `8AD` and `7AD` expected-count vectors MUST be digest-frozen before their target counts are read.
7. The preregistered U5-style diagnostic is `r=chi2/ndf` with per-partition band `|r-1|<=1.96*sqrt(2/ndf)` plus the predeclared cross-partition consistency rule.
8. Current observed result is `r_8AD=2.687745401485687`, `r_7AD=2.6944734551552125`; therefore `collapse_pass=false`.
9. A failed manual lowering does not by itself set `candidate_is_false=true`; it establishes only that this frozen lowering failed its declared OOD collapse diagnostic.
10. Post-reveal retuning or replacement of the lowering cannot be counted as continuation of the same confirmatory receipt.
11. A second or later distinct lowering for the same candidate MUST carry a pre-reveal multiplicity/alpha ledger with a family id, monotonically increasing attempt index, explicit positive debit for every prior distinct attempt, positive debit for the new attempt, a declared allocation rule and cumulative debit not exceeding the declared family-alpha budget. Retry-until-lucky without such spending SHALL fail closed. Replaying the identical lowering digest is not a new attempt.
12. A data-independent structural lowerability audit SHALL cover all 447 U4 candidates. `SINGLE_FORWARD_OWNER_COMPLETE` requires one existing source-law passport to cover every candidate axis through `scientific_coordinate` and to declare a parsed relation plus observable. `COMPOSABLE_MULTI_OWNER_COMPLETE` is weaker and SHALL NOT be interpreted as a frozen numeric lowering. Current census is 14 strict single-owner, 286 composable multi-owner, 9 axis-complete/no-forward, 134 partial-mapping/forward-present, 4 no-forward/no-complete-mapping.
13. The structural audit and lowerability metadata are diagnostic proposals for future U1–U2 admission; global enforcement remains false in 15.23.0.
14. `candidate_prediction_lowerings=1`, `candidate_prediction_discriminations=1`, `manual_prediction_collapse_pass_count=0`, `WORLD=0`, `U5=0` are required current-state invariants.
15. Joint qualification MUST execute the integrated Resident AI path in one isolated fresh process. Resident MUST execute its Cognitive Core dependency exactly once and expose that dependency status/digest in the Resident receipt; joint MUST bind both Cognitive and Resident receipts from that same live path. Duplicate Cognitive execution for bookkeeping is forbidden. Process-global AI resources MUST NOT be shared with QPDTR/multidomain owners inside the parent interpreter.

## 15.23.0 — observability / prediction-space contract

13. Atlas SHALL distinguish an open `Discovery Frontier` from an `Empirical Frontier`. Lack of a current measurement route SHALL NOT delete or falsify a discovery-valid candidate, but SHALL prevent it from consuming the same U3–U5 empirical budget as a structurally addressable candidate.

14. Prediction-space diversity SHALL be indexed by the experiment/data contract: `N_P(D)`, never an unqualified `N_P`. Two candidates with the same physically fixed lowering signature and experimentally indistinguishable predictions under preregistered uncertainty belong to the same measurement-equivalence class for `D`.

15. `N_P(D)` SHALL NOT be optimized by introducing arbitrary lowering degrees of freedom. A new prediction class requires a physically justified precommitted prediction operator and a preregistered distinguishability threshold relative to the measurement uncertainty/resolution of `D`.

16. Missing observables that block an otherwise meaningful forward route SHALL be persisted as explicit measurement requests. Current DLR requests are stored in `data/measurement_requests/ATLAS_MEASUREMENT_REQUESTS_CURRENT.json`; their existence is not WORLD evidence and does not establish U5.

## Query-driven research contract — 15.24.0

1. Query mode MUST accept an explicit observation schema and MAY accept a natural-language question only as context; ambiguous bare symbols MUST NOT be silently resolved.
2. The default returned shortlist is 25 and MUST be configurable only within 10..100 unless an explicit larger request is made through a future contract revision.
3. The shortlist size MUST NOT be used as the multiplicity count. The receipt MUST preserve the complete number of subsets/groups/candidates examined.
4. Buckingham birth MUST operate on quantity-bearing owner symbols with canonical 7D dimensions, never directly on categorical scientific-coordinate axis IDs.
5. For exact nullity one, the primitive dimensionless group is a frozen candidate formula. Dimensional analysis alone does NOT establish that its constant is universal.
6. With a target, the coordinate \(\Pi\) MUST be frozen before any search over \(f(\Pi)\).
7. Whole-surface null calibration MUST replay every candidate considered by the query pipeline, including candidates not displayed to the user.
8. `SO WHAT` scoring is permitted only for a frozen mathematical candidate and cannot promote a law without OOD/world evidence.


## Multi-Π function-form query contract — 15.25.0

1. The authoritative dimensional object for every multi-Π query MUST be the exact rational seven-dimensional kernel `ker D` computed before target-dependent fitting.
2. The multi-Π function-form lane MUST execute only when `p = dim ker D > 1`; `p<=1` MUST remain on its existing scalar/one-coordinate path or fail closed for this lane.
3. The deterministic displayed π basis MAY be used for reproducibility, but MUST NOT be claimed as the unique physical parameterization of the kernel subspace.
4. Every π coordinate MUST be frozen before any target-dependent representation search, model selection, cross-validation, or null calibration.
5. The current polynomial function family MUST be described as a finite query grammar and MUST NOT be represented as Atlas's primary scientific search space or as an exhaustive space of mathematical functions.
6. A normal query tranche MUST request between 10 and 100 structural hypotheses. This bound is an execution/query budget only and MUST NOT be interpreted as a global ceiling on scientific axis order, interactions, future grammars, or Discovery Frontier exploration.
7. Standardization, coefficient estimation, rank checks, and predictions MUST be recomputed inside each training fold. Validation rows MUST NOT contribute to training-fold scaling or coefficients.
8. With at least three explicit validation groups, validation MUST use leave-one-group-out and the permutation null MUST preserve the group structure. The current `WITHIN_VALIDATION_GROUP` scheme is valid only under an explicitly recorded within-group exchangeability assumption.
9. Without explicit groups, deterministic K-fold validation and global row permutation MAY be used when row exchangeability is scientifically defensible.
10. The multiplicity surface MUST be the complete set of structurally fitted hypotheses, not the displayed shortlist. `return_limit` MUST NOT reduce the null replay surface.
11. For every target permutation, Atlas MUST refit every structurally fitted function hypothesis. Reusing observed-target coefficients, winner identity, standardization, or fitted predictions under the null is forbidden.
12. The familywise statistic MUST compare the observed best cross-validated score with the best score obtainable anywhere on the same replayed structural surface.
13. The finite-null resolution `1/(B+1)` MUST be reported. If it exceeds the requested significance level, the null result MUST be `INSUFFICIENT_NULL_RESOLUTION`, not PASS.
14. The selected cross-validation score MUST NOT be claimed as an unbiased post-selection estimate of future generalization. Independent holdout, regime transfer, or world replication remains required.
15. A dimensional target MUST carry `DIMENSIONAL_TARGET_REQUIRES_RESPONSE_SCALE_FOR_UNIVERSAL_COLLAPSE` unless an explicit dimensionless/scaled response has been preregistered. Dimensionless predictors alone do not make a dimensional response universal.
16. Partial measurements from unrelated publications MUST NOT be stitched into synthetic joint rows and described as world evidence for `F(Pi_1,...,Pi_p)`.
17. A multi-Π candidate without a complete candidate-bound joint observation table MUST remain `UNKNOWN` at U5; lack of such a table MUST NOT be converted into falsification.
18. `search_observations_for_function_forms` MUST remain exposed through the existing `LawSpaceAPI.READ_TOOLS`; parallel algorithm-bearing CLI/script implementations are forbidden.
19. The 15.25.0 synthetic four-Π control is qualification evidence for the implementation only and MUST NOT be counted as a new physical law, world attestation, or U5 pass.
20. Exact reproduction of the five 2026-09-08 cross-domain kernels establishes dimensional reproducibility only; novelty, applicability, the function form, causality, and world validity remain separate evidence questions.


## 15.25.0 exoplanet missing-axis example contract

1. `examples/exoplanets_dimensional_birth_of_G.ipynb` SHALL be an executable worked example, not a new scientific authority or promotion owner.
2. The notebook SHALL use the sealed local CSV and SHALL NOT require network access at execution time.
3. The release SHALL state that the historical 172-row/132-star raw table is absent; the sealed 50-row NASA subset SHALL NOT be labelled as that historical table.
4. `CONST-G`, its value and its registered dimension SHALL NOT be read before the exponent winner and generated dimension are frozen.
5. The structural shell SHALL be explicit and finite: all-three-nonzero primitive integer vectors with `e_a in [-4,4]`, `e_P in [-4,4]`, `e_M in [-3,3]`, modulo global sign. Its current cardinality SHALL be 172.
6. The current frozen winner SHALL be `(3,-2,-1)` on the sealed CSV, yielding generated dimension `(3,-1,-2,0,0,0,0)`.
7. The generated axis SHALL be checked with the existing exact rational dimensional kernel. No notebook-local floating null-space authority may replace it.
8. The augmented axis set `[a,P,M_star,C_generated]` SHALL have exact nullity `p=1` with group equivalent to `(3,-2,-1,-1)`.
9. Registry comparison to `CONST-G` and the optional `4*pi^2` numerical interpretation SHALL occur only post-freeze and SHALL be labelled post-hoc.
10. Passing the notebook SHALL NOT create WORLD attestation, U5, novelty, causality, fundamental-constant discovery, or an independent replication claim.

## EDA chip-design research contract — 15.26.0

1. `EDA-CHIP-DESIGN-RESEARCH/1.0.0` MUST remain the single Atlas owner for the first chip PPA pilot; synthesis/place/route/DRC/LVS algorithms MUST NOT be copied into Atlas.
2. The first live world backend MUST be an actual ORFS execution, with `sky130hd/gcd` the frozen pilot pair unless a new experiment is separately frozen.
3. The candidate pool, knob ranges, common warm start, strategy list, budget and random seed MUST be frozen before world metrics are consumed.
4. A missing OpenROAD/Yosys/KLayout/ORFS backend MUST return `CHIP_PILOT_BACKEND_UNAVAILABLE`; a synthetic or analytical substitute MUST NOT be reported as a chip result.
5. Timing MUST fail when final setup slack is missing/negative or the explicit setup-violation-count metric is missing/nonzero.
6. DRC MUST fail unless the explicit final sign-off `6_drc_count.rpt` receipt is present and zero; detailed-route DRC MUST NOT substitute for sign-off DRC.
7. LVS MUST fail unless an explicit positive netlist-match receipt is available. Missing/ambiguous LVS is never PASS.
8. A configuration failing timing, sign-off DRC, LVS, or final-GDS presence MUST NOT be eligible as the final PPA winner even if its numerical area/power/delay is small.
9. Search normalization MUST be computed from the common preregistered warm-start observations only and then frozen for all strategies.
10. Atlas acquisition MUST reuse the authoritative Query function-form implementation; a second independent polynomial-response owner is forbidden.
11. Random, Grid and Bayesian baselines MUST receive the same warm-start observations and the same evaluation budget as Atlas.
12. Exact duplicate configurations MAY be cached globally; cache reuse MUST NOT be counted as an extra physical evaluation for one strategy.
13. The Bayesian baseline MUST not read unevaluated world values or a hidden optimum.
14. A negative Atlas-vs-baseline outcome MUST be retained as a valid result and MUST NOT trigger same-trial hyperparameter retuning.
15. `qualification_oracle` is implementation qualification only. It MUST NOT contribute to U5, world attestation, semiconductor-law evidence, PPA superiority evidence or tapeout claims.
16. A live pilot may assign any Boolean value to `atlas_beats_all_baselines` only after all four equal-budget strategies have each reached at least one fully feasible design; otherwise the comparison MUST be `INCONCLUSIVE` with value `null`.
17. Release 15.26.0 MUST report real chip superiority as `UNKNOWN` until such a live receipt exists.
18. No result of this pilot alone establishes generalization to other RTL, PDKs, process corners, analog designs, reliability/yield constraints or fabrication readiness.

19. The shipped 15.26.0 GitHub world run MUST checkout ORFS commit `be0dca0b1fd41df54792b3012350cd52bccd99bb` before metrics are read; using a different ORFS revision requires a separately frozen experiment.


## CURRENT 0.15.27.0 — Function-language birth contract

### Authority and non-duplication

The sole Query function-form authority is `QUERY-DRIVEN-RESEARCH/1.2.0`. `FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT` belongs to `PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0`; it is a component, not a second owner or optimizer.

### Ordering invariant

```text
exact rational D → frozen ker(D) / Π coordinates
→ baseline polynomial CV
→ OOF residual diagnosis
→ optional function-language birth
→ born-language CV
→ dynamic whole-procedure permutation null
```

Target values cannot modify the exact π basis. Function-language birth changes `F`, never `ker D`.

### Birth invariant

A language may be generated only when both

\[
R_{poly}\ge r_{birth}
\]

and

\[
\max(operation\_signal)>\max(g_0,\sqrt{2\log(M)/n}).
\]

High error alone is insufficient; no minimum language count may be forced.

### Executable grammar invariant

The finite current Query tranche may instantiate `RATIONAL`, `EXPONENTIAL`, `LOGARITHMIC`, `PERIODIC`, `PIECEWISE`, `KERNEL`, and `LATENT`. This is an executable grammar for the current query, not the scientific space and not an assertion that other mathematics does not exist. Fold-dependent transformations are trained inside their folds. Rational near-zero denominators fail closed.

### Multiplicity invariant

If `\mathcal H(y)` is the residual-dependent hypothesis set, every permutation must reconstruct `\mathcal H(y^{(b)})` from the permuted target. Freezing the observed born language and permuting only its coefficients is forbidden. Familywise calibration uses the minimum CV risk over each regenerated complete surface.

### Claim invariant

The operation screen is not formal significance. Selected CV is not unbiased post-selection generalization evidence. Synthetic function-language controls cannot create mathematical novelty, WORLD evidence, U5 or scientific promotion.
