# Φ-Compiler / ScienceAtlas — Mathematical Book, CURRENT 0.15.29.0

## 0. Назначение

Φ-Compiler 15.4.0 рассматривает научное исследование как эволюцию представления, а не как выбор формулы из конечной библиотеки. Базовая задача:

```math
\boxed{
\text{данные}\rightarrow
\text{представление}\rightarrow
\text{гипотезы}\rightarrow
\text{эксперимент}\rightarrow
\text{новое представление}
}
```

Система обязана различать внутренний расчёт, пользовательский input, внешнюю ссылку и идею текстового ИИ.

---

# I. Состояние исследовательской системы

## 1. Research state

На цикле `k` определим

```math
S_k=(D_k,\mathcal A_k,\mathcal L_k,\mathcal H_k,\mathcal E_k,\Pi_k).
```

### 1.1 `D_k` — данные

Содержит observations, experiment receipts, domain-solver receipts и provenance.

### 1.2 `A_k` — оси

```math
\mathcal A_k=\mathcal A_k^{canonical}\cup\mathcal A_k^{research}.
```

Canonical axis — текущая квалифицированная координата, а не вечная истина.

### 1.3 `L_k` — язык

Определяет допустимые математические carriers/operations на текущем цикле.

### 1.4 `H_k` — гипотезы

Каждая гипотеза имеет собственный lifecycle и digest.

### 1.5 `E_k` — evidence

Residual, falsification, holdout, intervention, counterfactual и experiment evidence.

### 1.6 `Π_k` — provenance

Определяет происхождение каждого claim.

---

# II. Пространство осей

## 2. Текущий registry

Поставляемая версия содержит:

```text
13 domains
655 canonical axes
445 source-owner passports
2771 archived historical baseline candidate/control records (provenance only; not active frontier)
26 constants
24 computational methods
```

Но

```math
\boxed{655\neq\dim(\Phi)_{universal}}.
```

Это только snapshot:

```math
N_k=|\mathcal A_k^{canonical}|.
```

В следующем состоянии разрешено:

```math
N_{k+1}>N_k,
```

```math
N_{k+1}=N_k,
```

или

```math
N_{k+1}<N_k.
```

## 3. Axis birth

Если residual имеет структуру по новой координате `a`, AdaptiveAxisDiscovery строит research-local proposal.

Для исходов `Y` и контекстной координаты `A` информационный сигнал:

```math
IG(Y;A)=H(Y)-H(Y\mid A).
```

Но `IG>0` не доказывает причинность. Дополнительные checks могут включать independent studies, permutation null, leave-one-study-out и confounding diagnostics.

## 4. Axis lifecycle

Допустимы:

```text
RESEARCH
PROVISIONAL
CANONICAL
DEPRECATED
REPLACED
RETIRED
```

Старые оси остаются адресуемыми через lifecycle ledger.

### 4.1 Split

```math
a\mapsto(a_1,a_2)
```

если единая координата смешивает независимые режимы.

### 4.2 Merge

```math
(a_1,a_2)\mapsto a
```

если доказана квалифицированная эквивалентность.

### 4.3 Retire

Ось может уйти из active view, но не удаляется из provenance.

---

# III. Синтез гипотез

## 5. Принцип fair dovetail

Нет конечного списка «разрешённых законов». На каждом цикле исследуется одна конечная complexity shell.

Пусть observables:

```math
x=(x_1,\ldots,x_n),
```

а target:

```math
y.
```

Текущий executable generic shell использует мономы

```math
m_{\mathbf p}(x)=\prod_{i=1}^n x_i^{p_i},
\qquad
\sum_i p_i=d,
```

для текущего degree `d`.

Следующий research cycle может увеличить `d`. Глобального `d_max` в контракте нет.

## 6. Линейная комбинация generated terms

```math
\hat y=c_0+\sum_{j=1}^{M}c_jm_j(x).
```

Параметры определяются численно на train segment, после чего кандидат проверяется на held-out segment.

## 7. Размерностная типизация

Представим физическую размерность вектором

```math
D=(L,M,T,I,\Theta,N,J).
```

Для монома

```math
D(m_j)=\sum_i p_{ji}D(x_i).
```

Чтобы term входил в сумму target `y`, coefficient получает

```math
\boxed{D(c_j)=D(y)-D(m_j)}.
```

Это не ручное физическое правило конкретного домена, а общая typed algebra.

---

# IV. Добавление температуры в пространство энергии

## 8. Active и dormant axes

Наличие наблюдаемой координаты в research-space не означает её присутствия в текущем законе.

Разделим:

```math
\mathcal A_k=\mathcal A_k^{active}\cup\mathcal A_k^{dormant}.
```

`active`-оси доступны hypothesis synthesizer. `dormant`-оси наблюдаемы и доступны residual/Constraint/AxisDiscovery контуру, но **не входят в initial formula-space**.

Переход

```math
a:dormant\to active
```

разрешён только если residual evidence делает эту координату различающей и повторный held-out fit действительно улучшается.

## 9. Энергетический control

Начальное представление:

```text
target = observed_energy
active = {base_energy}
dormant = {temperature}
```

Следовательно начальная модель вообще не знает `temperature` как предиктор и исследует только функции `base_energy`.

На coupled control лучший initial candidate:

```math
\hat E=c_0+c_1E_{base}
```

имеет holdout NRMSE около

```math
0.22247.
```

Residual классифицируется и `AdaptiveAxisDiscovery` получает dormant-context `temperature`. Для него текущий run дал:

```math
IG(r;T)\approx0.64321\ \mathrm{bit}.
```

После этого — и только после этого — temperature переводится в active model-space. Новый fair-dovetail search рождает:

```math
\hat E=c_0+c_1E_{base}+c_2E_{base}T,
```

где тип коэффициента interaction-term определяется автоматически:

```math
D(c_2)=D(E)-D(E_{base})-D(T)=-D(T).
```

На synthetic control holdout NRMSE порядка

```math
3.6\times10^{-14}.
```

## 10. Negative control

Та же температура добавляется как dormant axis в идентичное энергетическое пространство, но hidden control-world не содержит температурной зависимости.

Требуемый результат:

```text
temperature remains DORMANT_AVAILABLE_AXIS
activated_axis_variables = []
```

То есть Atlas не имеет права включать координату в модель только потому, что исследователь предложил её добавить в пространство.

## 11. Epistemic boundary

Обе выборки являются `CONTROL_REFERENCE`. Их задача — проверить механизм

```math
\text{space augmentation}\to\text{residual}\to\text{axis activation}\to\text{new hypothesis},
```

а не доказать реальный термодинамический закон.

# V. Fit, holdout и lifecycle

## 11. Fit

Для design matrix `X` используется least-squares:

```math
\hat\beta=\arg\min_\beta\|X\beta-y\|_2^2.
```

## 12. Held-out error

```math
NRMSE=\frac{
\sqrt{N^{-1}\sum_i(y_i-\hat y_i)^2}
}{\operatorname{std}(y)}.
```

Если design rank недостаточен, candidate не может перейти в `TESTABLE`.

## 13. Lifecycle

```text
IDEA
  ↓
CANDIDATE
  ↓ identifiability
TESTABLE
  ↓ held-out survival
SURVIVOR
  ↓ independent falsification / evidence campaign
LAW-CANDIDATE
  ↓ Scientific Promotion
PROMOTED OWNER
```

Ни один internal fit не перепрыгивает цепочку.

---

# VI. Residual как источник нового пространства

## 14. Residual

```math
r_i=y_i-\hat y_i.
```

Atlas классифицирует residual structure, а не исправляет частные строки вручную.

## 15. Возможные transitions

### 15.1 Existing-axis refinement

Старая ось остаётся, меняется её локальная модель.

### 15.2 New-axis birth

```math
\mathcal A_{k+1}=\mathcal A_k\cup\{a_{new}\}.
```

### 15.3 Interaction coordinate

Например:

```math
a_{ij}=x_ix_j.
```

Такой term/axis должен появиться из residual evidence, а не потому, что разработчик заранее знает ответ.

### 15.4 Higher-order shell

```math
d\to d+1.
```

Порядок расширения не обязан расти по одной координате. Пусть (B_k) —
конечный пакет осей, который требуется структурой остатка, типизированными
мостами, взаимодействиями или условием идентифицируемости на цикле (k). Тогда

```math
\mathcal A_{k+1}=\mathcal A_k\cup B_k,
\qquad 0\le |B_k|<\infty,
```

причём (|B_k|) выбирается адаптивно и не имеет фиксированного значения.
Допустимы одновременное рождение нескольких осей и оси взаимодействий высших
порядков. Это защищает Atlas от жадной ошибки, когда физически или формально
значимая структура проявляется только совместно и невидима при добавлении
координат по одной.

Политика записывается как

```text
AXIS_BIRTH_CARDINALITY = ADAPTIVE
MULTI_AXIS_BIRTH = ALLOWED
HIGHER_ORDER_INTERACTION_AXES = ALLOWED
FIXED_AXIS_COUNT_PER_CYCLE = NONE
SEARCH = SPARSE + ADAPTIVE + OPEN_ENDED
```

`OPEN_ENDED` не означает бесконечную материализацию в памяти. Каждый запуск
строит конечное разреженное множество, сохраняет продолжение обхода и может
расширить его в следующем цикле. Каждая ось из (B_k) всё равно получает
собственную типизацию, provenance, admission и promotion receipt; совместная
номинация не является совместным автоматическим принятием.

### 15.5 Representation change

Если координат недостаточно, активируется Mathematical Invention.

---

# VII. Mathematical Invention

## 16. Unknown-unknown representation

Вход — независимые failure/evidence modes:

```text
residual
latent
causal
counterfactual
cross_domain_bridge
```

Выход — obligations, а не имя известного метода.

## 17. Primitive synthesis

Из transition observations строится минимальный finite carrier с `observe` и `update`.

Эквивалентные histories факторизуются:

```math
h_i\sim h_j
```

если они неразличимы по наблюдениям и переходам.

## 18. Morphism

Для generated objects `A,B` ищется

```math
f:A\to B
```

с явными множествами

```text
Preserve
Lose
```

## 19. Controlled limit

Новый объект может восстанавливать старый в контролируемом пределе только если state/update/observable errors одновременно демонстрируют устойчивый limit-law.

---

# VIII. Competing hypotheses

## 20. Почему число 5 больше не запрет

Исторически система требовала минимум пять механизмов до движения дальше. Это полезно как защита от premature convergence, но вредно как универсальное логическое правило.

В 15.2.8:

```math
N_{target}=5
```

— search-pressure target.

Если реально существуют только два различимых кандидата, система может проектировать эксперимент между ними. Если один кандидат единственный только из-за бедности генератора, фиксируется coverage gap.

Правило истины не зависит от `N=5`.

---

# IX. Различающий эксперимент

## 21. Exact EIG

Если имеются явные likelihoods:

```math
P(o\mid h,e),
```

можно вычислять

```math
EIG(e)=H(H)-\sum_oP(o\mid e)H(H\mid o,e).
```

Likelihoods запрещено придумывать текстовому слою.

## 22. Deterministic disagreement proxy

Если probability model отсутствует, Adaptive Research Kernel может использовать только явно не-EIG score:

```math
V(e)=\operatorname{Var}_{h\in\mathcal H}\hat y_h(e).
```

Статус:

```text
DISAGREEMENT_EXPERIMENT_RANKED_NOT_PROBABILISTIC_EIG
```

---

# X. Provenance

## 23. Origins

```text
ATLAS_NATIVE
USER_SUPPLIED
EXTERNAL_REFERENCE
ASSISTANT_HYPOTHESIS
CONTROL_REFERENCE
UNKNOWN
```

## 24. Atlas execution receipt

`ATLAS_NATIVE` требует:

```text
owner
schema
input_digest
axis_registry_digest
hypothesis_space_digest
code_digest
result_digest
digest
```

`code_digest` связывает current research-cycle/adaptive-axis/mathematical-invention/law-discovery source files.

## 25. Firewall theorem of operation

Если

```math
digest(receipt\setminus\{digest\})\neq receipt.digest,
```

то

```text
ATLAS_NATIVE = REJECTED.
```

Если issuer не `ADAPTIVE-RESEARCH-KERNEL/15.4.0`, claim также rejected.

## 26. Atlas-native не равно law

```math
ATLAS\_NATIVE\Rightarrow\text{provenance valid}
```

но

```math
ATLAS\_NATIVE\not\Rightarrow\text{scientific truth}.
```

---

# XI. AI boundary

## 27. Роль LLM

Text/LLM layer может:

- сформулировать research question;
- предложить observable;
- предложить эксперимент;
- описать результат receipt.

LLM не может:

- присвоить `ATLAS_NATIVE`;
- установить `ESTABLISHED_LAW`;
- объявить `CONFIRMED_CONSTANT`;
- объявить `EXPERIMENT_PASS` без authoritative receipt.

## 28. API firewall

`propose_candidate` принудительно задаёт:

```text
claim_origin = ASSISTANT_HYPOTHESIS
atlas_native = false
promotion_allowed = false
```

если это proposal от AI-facing layer.

Public surface разделён на попарно непересекающиеся классы

```math
\mathcal T_{pub}=\mathcal T_R\,\dot\cup\,\mathcal T_M\,\dot\cup\,\mathcal T_G,
```

где `R=READ`, `M=MUTATION`, `G=REGRESSION`. Для каждого public method `m`:

```math
\sum_{X\in\{R,M,G\}}\mathbf 1[m\in\mathcal T_X]=1.
```

Answer-bearing historical/post-freeze atomic routes принадлежат только `REGRESSION_TOOLS`. Их вызов требует явного `regression_mode=True`; при default/blind execution они fail-closed до чтения regression evidence. Это отделяет воспроизводимость старых экспериментов от источника данных для нового blind search.

---

# XII. Owner-connected Φ-space

## 29. Directed search

Каждый research cycle выполняет directed owner-hypergraph search по текущему registry.

Текущий registry содержит 655 canonical axes, но scan receipt обязан явно фиксировать:

```text
fixed_axis_count_ceiling = None
```

на уровне research contract.

## 30. Candidate registry

2 771 baseline records — controls/anchors, а не полный solution space.

```math
\mathcal H_{possible}\not\equiv\mathcal H_{registry}.
```

Void/sparse regions не равны физическому отсутствию; они являются frontier targets.

---

# XIII. Cross-domain research

## 31. Без заранее существующего bridge для поиска

Joint tuple exploration между доменами допускается до наличия bridge.

Но арифметическое/физическое отождествление требует typed mapping/bridge contract.

Это позволяет искать неожиданные связи без нарушения dimensional semantics.

---

# XIV. Existing domain owners

## 32. Сохранённые области

Current runtime включает:

```text
aeronautics_and_aerostation
astronomy
biology
chemistry
earth_systems
materials_science
mathematics
mechanics
metrology
pharmaceutical
physics
quantum_information_and_computational_methods
systems_control
```

Adaptive Research Kernel не копирует их numerical logic.

## 33. Physics regressions

Сохраняются Einstein/tensor/black-hole, neutrino, particle-space, quantum-vacuum и другие owners.

## 34. Atomic regression

Atomic research program остаётся benchmark того, как representation должен меняться при росте сложности. Его high-Z claims не являются universal architecture constraints. Исторические formal-slot/high-Z receipts, включая участки с фиксированными atomic ranges, сохраняются как regression evidence, а не как blind priors.

Default research contract:

```math
\mathcal E_{blind}\cap\mathcal E_{answer\text{-}bearing\ regression}=\varnothing.
```

Доступ к таким owners возможен только через явный regression opt-in. Поэтому наличие старого `118/172`-ориентированного benchmark-кода не задаёт верхнюю границу новому blind Atlas path.

Current sequential atomic receipt имеет status:

```text
PHYSICAL_SEQUENCE_UNDERIDENTIFIED_CROSS_DOMAIN_GAP
```

и explicitly:

```text
stop_is_physical_Zmax = false.
```

---

# XV. Single-step adaptive protocol

## 35. Input

```text
question
domain_id
target_variable
predictor_variables
variable_dimensions
observations
observations_origin
complexity_level
previous_state (optional)
experiment_points (optional)
```

## 36. Execution

```text
normalize input
→ owner-connected scan
→ bind current representation
→ synthesize current complexity shell
→ fit + held-out test
→ residual analysis
→ AdaptiveAxisDiscovery
→ Mathematical Invention if needed
→ experiment disagreement/EIG
→ next_state
→ Claim Firewall
```

## 37. Output state

`next_state` содержит:

```text
problem_id
research_local_axes
complexity_level
surviving_hypothesis_ids
best_hypothesis_id
previous_state_digest
state_digest
```

Это позволяет выполнять исследование строго по одному шагу без скрытого глобального потолка.

---

# XVI. Инварианты 15.2.8

## 38. Архитектурные

```text
ONE authoritative adaptive research kernel
NO fixed universal axis ceiling
NO fixed global hypothesis complexity ceiling
NO candidate registry = solution space
NO AI → ATLAS_NATIVE shortcut
NO external reference → ATLAS_NATIVE relabel
NO fit → law shortcut
NO blind/default → answer-bearing regression receipt
ALL public API methods classified exactly once
IMMUTABLE report evidence digest-bound
```

Release-integrity state задаётся

```math
\mathcal S_{seal}=H(\mathcal C)\oplus H(\mathcal R_{immut})\oplus B(\mathcal R_{mutable}),
```

где `C` — controlled source/data/configuration files, `R_immut` — полный ledger неизменяемых report/evidence artifacts, а `B(R_mutable)` — manifest bindings для фиксированного множества current replay outputs. Любое изменение immutable evidence требует rebuild/reseal; расширение mutable whitelist без rebuild также нарушает seal.

## 39. Научные

```text
UNKNOWN != FALSE
FAILED PROMOTION != FALSIFIED
RESIDUAL MAY EXPAND REPRESENTATION
PROMOTION REQUIRES EVIDENCE
```

---

# XVII. Исполнимый synthesis representation

## 40. Black-box operator evidence

Когда текущий representation не закрывает residual, новый путь не требует заранее назвать известное уравнение. Вводом служат attested operator-response probes

```math
\mathcal D_{\rm op}=\{(x,\psi^{(q)},y^{(q)})\},
\qquad y^{(q)}=\mathcal O\psi^{(q)}.
```

Discovery и sealed holdout разделены до поиска. Значения sealed probes не участвуют в выборе структуры оператора.

## 41. Operator grammar

На текущем complexity shell безопасный typed grammar содержит базисы

```math
I,\qquad \partial_x,\qquad \partial_x^2,\qquad x^p I,
\quad p\in\{-2,-1,1,2\},
```

для каждого входного/выходного компонента. Межкомпонентные block terms допускаются автоматически. Это current grammar, а не универсальный список всех возможных операторов.

Для компоненты `a` кандидат имеет форму

```math
(\widehat O\psi)_a
=
\sum_{b,j} c_{abj}\,B_j\psi_b.
```

Коэффициенты и sparsity support выводятся из discovery evidence детерминированным forward sparse search. Структура freeze-ится до sealed holdout.

## 42. Probe objective

Для output component `a` минимизируется discovery residual

```math
\varepsilon_a^{\rm disc}
=
\frac{\|y_a-X_a c_a\|_2}{\max(\|y_a\|_2,\epsilon)}.
```

После freeze вычисляется независимый

```math
\varepsilon_a^{\rm sealed}
=
\frac{\|y_{a,*}-X_{a,*}c_a\|_2}{\max(\|y_{a,*}\|_2,\epsilon)}.
```

Только если все output components проходят declared tolerance, artifact получает статус `GENERATED_EXECUTABLE_OPERATOR_CANDIDATE`.

## 43. Compilation

Theory Compiler строит immutable IR, а не Python/source code:

```text
GENERATED_TYPED_OPERATOR_PROGRAM
→ TYPED_CONTINUOUS_OPERATOR_PROGRAM
→ deterministic matrix assembly
→ eigen/fixed-point runtime
```

`eval`, `exec`, arbitrary generated source и named domain solver selection запрещены.

## 44. Standard и generalized eigenproblem

Для frozen grid компилируются задачи

```math
A\psi=\lambda\psi
```

и

```math
A\psi=\lambda B\psi.
```

Runtime возвращает для каждой пары residual

```math
r_\lambda
=
\frac{\|A\psi-\lambda B\psi\|}
{\max(\|A\psi\|+|\lambda|\|B\psi\|,\epsilon)}.
```

## 45. Self-consistent fixed point

IR может содержать typed local fields `V_j` и safe update operators. Общий цикл:

```math
A[V^{(n)}]\psi^{(n)}=\lambda^{(n)}B\psi^{(n)},
```

```math
\rho^{(n)}=\rho(\psi^{(n)}),
```

```math
\widetilde V^{(n+1)}=F(\rho^{(n)}),
```

```math
V^{(n+1)}=(1-\eta)V^{(n)}+\eta\widetilde V^{(n+1)}.
```

Convergence определяется field residual, а не номером предметной области. Current safe updates включают density-power и Poisson-response forms; их наличие не означает, что они автоматически правильны для конкретной физики.

## 46. Gap protocol и Atlas-native probe birth

Если operator-response evidence отсутствует, Atlas теперь разделяет **рождение входа эксперимента** и **получение ответа мира**. Сначала `OPERATOR-PROBE-DESIGN/2.1.0` строит только states:

```math
\mathcal P_0=\{(x,\psi^{(q)},\mathrm{role}_q)\},
\qquad y^{(q)}\;	ext{неизвестно}.
```

Для текущего grammar строится feature matrix

```math
X(\mathcal P_0)=\big[B_j\psi^{(q)}\big]_{q,j}.
```

Atlas greedily выбирает probe inputs так, чтобы достигнуть максимального rank и улучшить минимальное singular value нормированной feature matrix. Число probes не является физическим потолком: текущий `design_shell` конечен, а `next_design_shell_exists=true`. Discovery inputs и sealed-holdout inputs freeze-ятся **до** появления response values.

Если текущий shell идентифицирует grammar, статус:

```text
OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES
```

а общий research status:

```text
REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES
```

Это не measurement и не разрешение AI придумать `y`. Следующая операция обязана получить response из world attestation или authoritative typed owner.

Если probes существуют и candidate проходит sealed gate:

```text
EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW
```

После этого обязательна независимая falsification/promotion стадия.

### 46.1 Direct gap-entry и strict-blind atomic control

В 15.2.8 representation gap является полноценным executable entry point. Capability-gap receipt проходит без фиктивных observations только при наличии `gap_evidence`/`gap_evidence_digest`. При `blind_no_named_law_catalog=true` named-law scan подавляется, а шесть answer-bearing atomic/high-Z regression surfaces обязаны fail-closed без `regression_mode=True`.

Strict-blind atomic control не задаёт число объектов или верхний индекс. Начальный negative control без response owner остаётся обязательным и заканчивается:

```text
REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES
```

Atlas самостоятельно рождает response-free probes. Первый одно-компонентный shell имеет

```math
\operatorname{rank}X=7/7,
```

и freeze-ит `3` discovery + `1` sealed-holdout probe до появления любого response.

### 46.2 Independent typed reference-world owner

Недостающий world-interaction контракт реализован существующим Theory Compiler owner:

```text
ATOMIC-REFERENCE-WORLD-INTERACTION/1.0.0
```

Его граница:

```math
\mathcal P_{\rm frozen}
\xrightarrow{\;W_{\rm ref}\;}
\{(\psi^{(q)},\,\mathcal O_{\rm ref}\psi^{(q)})\}_q.
```

`W_ref` — **reference simulation**, не empirical world measurement. Она разрешена только явным opt-in, проверяет digest frozen protocol и не может принимать probes с уже заполненными responses. До freeze synthesis-path не получает ни имя известного уравнения, ни коэффициенты reference model, ни готовую solver structure. `atomic_frontier.py` этим owner не импортируется.

World owner может вернуть только typed carrier requirement. В фактическом control первый Atlas protocol был одно-компонентным; owner ответил `TYPED_CARRIER_REDESIGN_REQUIRED` с требованием двух компонент. После этого именно Atlas заново породил protocol:

```math
\operatorname{rank}X=14/14,
```

с `5` discovery и `2` sealed-holdout probes. Минимальное нормированное singular value этого shell положительно; holdout inputs были freeze-нуты до responses.

После freeze reference owner вернул только response rows и digest-bound attestation. Post-freeze audit раскрывает использованную established reference simulation:

```math
V(r)=-\frac1r,\qquad c=\alpha^{-1},\qquad \kappa=-1,
```

```math
\begin{aligned}
y_0 &= V f_0+c\left(-\partial_r f_1+\kappa\frac{f_1}{r}\right),\\
y_1 &= c\left(\partial_r f_0+\kappa\frac{f_0}{r}\right)
      +\left(V-2c^2\right)f_1.
\end{aligned}
```

Эта формула является **audit reference после freeze**, а не prior для Atlas synthesis.

### 46.3 Что восстановил Atlas из responses

Из одних frozen `state -> response` rows общий operator synthesizer восстановил ненулевые блок-термы:

```math
\begin{aligned}
O_{00}&\approx-\,r^{-1},\\
O_{01}&\approx-\,c\,\partial_r-c\,r^{-1},\\
O_{10}&\approx+\,c\,\partial_r-c\,r^{-1},\\
O_{11}&\approx-2c^2 I-r^{-1}.
\end{aligned}
```

Численно recovered coefficients совпадают с reference-world coefficients до floating-point precision. Discovery normalized residuals и sealed-holdout residuals порядка `10^-16`; holdout не использовался для pruning/term selection. Скомпилированный executable IR проходит numerical eigenproblem с maximum eigen residual порядка `10^-16`.

Фактический статус:

```text
EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW
```

То есть Atlas действительно замкнул цикл

```math
\boxed{
\text{gap}
\to\text{Atlas probe birth}
\to\text{carrier feedback/redesign}
\to\text{frozen protocol}
\to\text{independent reference responses}
\to\text{synthesis}
\to\text{compile}
\to\text{execute}
\to\text{sealed falsification}
}
```

без использования answer-bearing atomic regression до freeze.

## 47. Variable-particle / self-consistent frontier

После однопarticle representation Atlas продолжает тот же blind цикл, не получая заранее ни many-electron solver, ни верхнее число объектов. Owner `VARIABLE-PARTICLE-PROBE-DESIGN/1.0.0` рассматривает число частиц только как экспериментальную координату и сам рождает full-rank protocol по признакам

```math
1,\qquad N-1,\qquad (N-1)^2.
```

В текущем frozen run Atlas выбрал discovery counts `{2,1,3}` и sealed holdout `N=4`; это не утверждение существования атомов с такими индексами и не `Zmax`.

Независимый `ATOMIC-VARIABLE-PARTICLE-REFERENCE-WORLD/1.0.0` после freeze возвращает для каждого frozen state только typed rows `(N, psi, rho, F, O psi)`. Hidden audit model не передаётся synthesis-path до freeze.

Generic owner `SELF-CONSISTENT-REPRESENTATION-SYNTHESIS/1.0.0` идентифицирует

```math
\mathcal O_{\rm sc}[F]\psi
=\mathcal O_0\psi+G[F]\psi
```

и field update

```math
(-\partial_x^2+\lambda I)F=(aN+b)\rho.
```

В reference control Atlas восстановил диагональный field multiplication coefficient `~1`, `a~1`, `b~-1`, `lambda~0.5`; discovery и sealed-holdout errors находятся около machine precision. Затем compiler lowered candidate в `SELF_CONSISTENT_EIGENPROBLEM`, а runtime достиг `FIXED_POINT_CONVERGED`.

Фактический статус:

```text
SELF_CONSISTENT_EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW
```

Scientific boundary остаётся жёсткой: это reference-simulation qualification, не empirical atom/nucleus evidence. Никакой probed particle count не становится автоматически физически существующим элементом.

Следующий frontier:

```text
PHYSICAL_OBJECT_EXISTENCE_AND_NUCLEAR_STABILITY_WORLD_EVIDENCE_REQUIRED
```

Требуются как минимум:

```text
NUCLEAR_BINDING_AND_DECAY_WORLD_RESPONSE
OBJECT_EXISTENCE_VERSUS_PARTICLE_COUNT
MULTI_SCALE_ELECTRON_NUCLEUS_COUPLING_FALSIFICATION
```

Следовательно,

```math
Z_{\max}=\mathrm{UNKNOWN},
```

`scientific_law_established=false`, `physical_atom_existence_established=false`, `periodic_table_genesis_completed=false`.


# XVIII. Что ещё не решено универсально

## 48. Полнота operator grammar

Текущий grammar не доказывает универсальный synthesis произвольных PDE, integro-differential, stochastic, nonlocal или variable-topology theories. Residual может потребовать рождение новых primitives.

## 49. Experiment world access

Kernel может спроектировать эксперимент, но реальный world measurement должен поступить через authoritative instrument/domain owner.

## 50. Novelty

Internal absence не доказывает world novelty.

## 51. Causality

Predictive fit не равен causal law. Intervention/counterfactual evidence требуется отдельно.

## 52. Historical autonomous/Gamma evaluator

`evaluation.autonomous_research_orchestration_qualification` сохраняется как historical compatibility/evidence evaluator из линии 11.x и **не является current acceptance gate**. Контрольный запуск исходного 15.2.0 и 15.2.8 одинаково даёт `48/50`: не проходят aggregate gates `GAMMA_all_internal_gates_pass` и `GAMMA_structural_candidate_frozen`; historical Gamma path остаётся fail-closed. Это не регрессия 15.2.8 и не должно «исправляться» ослаблением current gates. Если этот legacy path снова потребуется как active capability, его нужно модернизировать отдельным различающим экспериментом и затем включить в current acceptance явно.

## 53. Module/static architecture audit

Ревизия current tree фиксирует 59 `source`-модулей. Все 59 импортируются в current test inventory; AST parse всего Python tree проходит без syntax errors. В `source` нет `TODO/FIXME` и нет `NotImplementedError`. Четыре bare `pass` находятся только в exception-fallback ветках (`qpdtr_bridge`, `constraint_atlas`) и не являются заглушками solver-path.

Top-level import graph `source` является ацикличным. Более крупный callback/call graph содержит взаимные локальные owner-вызовы между research orchestration и domain owners; это runtime orchestration, а не import-time circular dependency. Нулевой source-inbound у entry/adaptor modules (`api`, `model_selection`, `multidomain_qg_bridge`, `phi_compiler_owner`, `qpdtr_bridge`) проверен против evaluation/interfaces: они используются как внешние entry surfaces, а не признаны dead code.

В current Python tree не найдено вызовов `eval()`/`exec()`. Process spawning ограничен resident/reflexive isolation owners; сетевой доступ находится в scientific verification/data-ingestion owners и hardware instrument adapters, а не внутри Theory Compiler synthesis runtime.

---

# XIX. Текущий критерий следующего развития

Следующий релиз должен расширять не список domain-specific правил, а общую способность одного ядра:

```math
\boxed{
\text{Residual}
\to
\text{Axis/Primitive Birth}
\to
\text{Discriminating Experiment}
\to
\text{Falsification}
\to
\text{Representation Evolution}
}
```

Любая новая domain feature считается правильной архитектурно только если она подключается к этому циклу как owner/experiment/evidence source, а не создаёт параллельный исследовательский алгоритм.



## Open-ended periodic frontier and set-valued identifiability

The active periodic-table controller has **no numerical terminal atomic number**. Its physical scan is defined by

\[
Z_{k+1}=Z_k+1,\qquad
\text{continue iff }E_{\mathrm{existence}}(Z_{k+1})\land E_{\mathrm{representation}}(Z_{k+1})\land E_{\mathrm{falsification}}(Z_{k+1})\text{ are admissible}.
\]

There is no `max_Z`, `124`, `172`, or visit-count stop in this rule. A physical scan terminates only at the first typed evidence/representation gap. In the current sealed evidence state, the closed world-attested prefix ends at `Z=118`, while `Z=119` has unresolved physical-object existence/nuclear-stability evidence. Therefore the current result is **not** a newly inferred `Zmax=118`; it is

```text
last_closed_physical_prefix_Z = 118
first_unresolved_Z            = 119
Zmax_identified               = false
```

Electronic hypothesis generation is deliberately separated from physical existence. For added-electron count `q=Z-118`, the initial frontier is `8s,8p,7d,6f,5g`. If its finite capacity is insufficient, Atlas births further research-local angular channels `RL_l5, RL_l6, ...` with capacity `2(2l+1)`; their energy ordering is **not** supplied. The electronic candidate count is represented symbolically as the coefficient

\[
|\mathcal H_Z|=[x^q]\prod_i(1+x+\cdots+x^{c_i}),
\]

so the hypothesis space does not require exhaustive materialization and has no baked-in upper `Z`. A finite `z_values` request is merely a diagnostic view of this symbolic space, never a physical-table length.

When `|\mathcal H_Z|>1`, the authoritative electronic result is `IDENTIFIABILITY_GAP`; mixtures remain admissible and no single ground-state label is promoted. `Z\alpha` remains an active hypothesis coordinate. The experiment portfolio starts with first-ionization threshold, resonance-level spectroscopy and fine/hyperfine/magnetic structure, while a separate nuclear binding/decay/object-existence experiment is required before any new row may enter the physical table.

The historical 172-row X-LDA artifact is retained only as quarantined regression evidence. Its length is metadata of that frozen artifact, not an architectural or physical limit.

# XX. Open-ended nuclear binding / decay / object-existence world interaction

The current nuclear frontier is not a fixed table extension.  The authoritative nuclear owner is

`NUCLEAR-BINDING-DECAY-WORLD-INTERACTION/1.0.0`.

Its physical scan has no configured upper proton number, neutron number, or visit budget:

\[
Z=Z_0,Z_0+1,\ldots,\qquad N\in\mathbb N,
\]

and advances from a proton number only when world evidence contains at least one non-estimated, Z-identified nuclide whose attested lifetime satisfies

\[
\tau(Z,N)\ge 10^{-14}\ \mathrm{s}.
\]

This is an evidence gate, not a model prediction.  Failure to find a qualifying attestation is represented as UNKNOWN/UNATTESTED and is never converted into a proof of non-existence.

## XX.1 Gross reference mass surface

The existing SEMF owner is retained only as a reference-model generator.  Its mass surface is

\[
B(A,Z)=a_vA-a_sA^{2/3}-a_c\frac{Z(Z-1)}{A^{1/3}}-a_a\frac{(A-2Z)^2}{A}+\delta(A,Z).
\]

The historical scan maximized total \(B\), which is not a stable isotope-selection objective because total binding grows approximately with particle count.  The current owner instead searches adaptively in neutron number and maximizes

\[
\boxed{\frac{B(A,Z)}{A}}
\]

while expanding the N-domain until the optimum is interior and the far tail is demonstrably worse.  There is no fixed `Nmax`.

The reference observables include

\[
S_n=B(Z,N)-B(Z,N-1),\qquad S_{2n}=B(Z,N)-B(Z,N-2),
\]

\[
S_p=B(Z,N)-B(Z-1,N),\qquad S_{2p}=B(Z,N)-B(Z-2,N),
\]

and

\[
Q_\alpha=B(Z-2,N-2)+B_\alpha-B(Z,N).
\]

They are falsifiable model outputs, not attestations of isotope existence.

## XX.2 Partial alpha-decay models and the missing total lifetime

Two independent empirical alpha-decay parameterizations are carried as reference observables: the Viola-Seaborg-Sobiczewski form and the Universal Decay Law.  Their disagreement is recorded as model spread rather than hidden by model selection.

For the VSS form,

\[
\log_{10}T_{1/2}^{(\alpha)}=\frac{aZ+b}{\sqrt{Q_\alpha}}+(cZ+d)+h_{\log},
\]

and the UDL is evaluated in its standard cluster-decay coordinates.  These values are **alpha partial half-lives only**.

The current Atlas does not yet possess a qualified spontaneous-fission barrier/action owner or beta/EC partial-rate owner.  Consequently

\[
\boxed{T_{1/2}^{\rm total}=\mathrm{UNKNOWN}}
\]

whenever those channels can compete.  A long predicted alpha partial half-life may not be relabelled as a long-lived physical element.

## XX.3 Evidence and reference-simulation separation

The nuclear world owner exposes two non-interchangeable paths:

\[
\text{ATTESTED WORLD EVIDENCE}\rightarrow\text{physical advance gate},
\]

\[
\text{REFERENCE SIMULATION}\rightarrow\text{hypothesis + discriminating experiments only}.
\]

The reference path may propose isotope ridges, separation energies, alpha Q-values, and alpha partial lifetimes.  It cannot establish a physical element, an island of stability, or a terminal \(Z_{\max}\).

For the first unresolved proton number the owner ranks the next measurements as: correlated production/decay-chain lifetime and Z-linked daughter evidence; mass/Q-alpha closure; spontaneous-fission partial lifetime; and one-/two-nucleon separation energies.  These are experiment contracts, not claimed observations.

## XX.4 Current physical frontier

With no new attested nuclide rows supplied to the owner, the open-ended scan reaches

\[
Z=119
\]

and returns

`STOPPED_AT_FIRST_UNRESOLVED_NUCLEAR_EXISTENCE_GATE`.

This statement means only that the current evidence set has no qualifying attestation for the next proton number.  It does **not** mean that element 119 does not exist, and it does not identify 118 as a physical theorem for the last possible element.

The next representation frontier is therefore microscopic nuclear structure and competing decay dynamics:

\[
\boxed{
(Z,N,\beta_2,\beta_3,\ldots)
\rightarrow
E_{\rm HFB/DFT}
\rightarrow
\text{fission path/barrier}
\rightarrow
S_{\rm action}
\rightarrow
T_{\rm SF}
\rightarrow
\{T_\alpha,T_{\rm SF},T_\beta,T_{\rm EC},\ldots\}
}
\]

followed by blind comparison with attested masses and decay chains.  Only after those competing channels are identified can Atlas attempt a physical lifetime and continue the evidence-driven periodic frontier.


# XXI. Electronic State-Space Search — 15.4.0

## 51. Разделение пространства поиска и численного evaluator

Электронная задача больше не определяется цепочкой

\[
\text{Aufbau/Madelung}\to C_Z\to E(C_Z).
\]

Authoritative domain owner — `ELECTRONIC-STATE-SPACE-SEARCH/1.1.0`. Численный Dirac/SCF код является отображением

\[
\mathcal E_D:(Z,n,\kappa,V)\mapsto(\varepsilon,P,Q),
\]

\[
\mathcal E_{SCF}:(Z,C,R_N,\alpha_x,\mathcal G)\mapsto(E,\rho,V,\mathrm{residual}),
\]

где \(C\) — уже сформулированная occupation hypothesis, \(R_N\) — явная finite-nucleus hypothesis с provenance, а \(\mathcal G\) — numerical discretization. Ни одно из этих отображений не является владельцем выбора физической конфигурации.

## 52. Электронное Φ-пространство

Для нейтрального атома текущий research-local state можно записать

\[
X_Z=(Z,\mathcal A_e,C,\mathcal R,H,\theta,\mathcal G,E,\Delta),
\]

где

\[
\mathcal A_e\supset\{n,l,j,\kappa,q,R_N,\alpha_x,\text{representation},\text{correlation-response},\ldots\}.
\]

Число доступных quantum shells не является физическим потолком:

\[
 n_{\max}=\varnothing,\qquad l_{\max}=\varnothing.
\]

Это не означает бесконечный массив в памяти. Каждый executable cycle исследует конечную computational shell, а boundary pressure разрешает открыть следующую. Таким образом finite execution и open-ended scientific topology разделены.

## 53. Proposal без таблицы конфигураций

Central-potential owner численно строит radial eigenstates. Для регулярного central-potential state radial-node coordinate \(r_i\) переводится в principal coordinate

\[
n=r_i+l+1.
\]

Это преобразование координат, а не правило энергетического порядка. Полученная occupation \(C_0\) имеет provenance `NUMERICAL_CENTRAL_POTENTIAL_PROPOSAL` и **не является ответом**.

Из frontier occupied states рождаются legal occupation transfers

\[
C' = C-e_{n_1l_1}+e_{n_2l_2},
\]

при

\[
q_{n_1l_1}\ge1,
\qquad
q_{n_2l_2}<2(2l_2+1),
\qquad
0\le l_2<n_2.
\]

Element names, known anomalies, published superheavy orderings и correction-label vocabulary в генерации отсутствуют.

## 54. Finite-nucleus relativistic evaluator

Radial Dirac evaluator решает

\[
\frac{dP}{dr}=-\frac{\kappa}{r}P+\frac{2c^2+\varepsilon-V}{c}Q,
\]

\[
\frac{dQ}{dr}=\frac{\kappa}{r}Q-\frac{\varepsilon-V}{c}P.
\]

Для finite nucleus в SCF используется явная сферическая charge hypothesis радиуса \(R_N\). Сам evaluator не строит \(R_N(Z)\). Источник `R_N` обязан быть указан в receipt. В 15.4.0 текущий default provider — reference candidate nuclear owner; поэтому такой radius не является empirical world measurement.

Average-of-configuration relativistic split имеет вид

\[
q_{nlj}=q_{nl}\frac{2j+1}{2(2l+1)},
\]

и является частью representation, а не доказанным many-body ground state.

Dirac-Slater functional evaluator:

\[
E_{\rm tot}=\sum_i q_i\varepsilon_i-E_H-\frac14\int D(r)V_x(r)\,dr,
\]

\[
V_H(r)=\frac1r\int_0^rD(r')dr'+\int_r^\infty\frac{D(r')}{r'}dr',
\]

\[
V_x(r)=-3\alpha_x\left(\frac{3\rho(r)}{8\pi}\right)^{1/3}.
\]

`alpha_x` является явным representation parameter и участвует в sensitivity test.

## 55. Stability gate вместо «минимум = истина»

Пусть \(C_*\) — минимум в основной representation, \(C_*^{(g)}\) — минимум после grid refinement и \(C_*^{(x)}\) — минимум при независимом perturbation exchange representation. Provisional selection разрешён только если

\[
C_*=C_*^{(g)}=C_*^{(x)}
\]

и, при наличии runner-up,

\[
\Delta E_{12}>2\,\delta E_{num},
\]

где \(\delta E_{num}\) — observed energy spread от discretization refinement.

При нарушении gate:

```text
REPRESENTATION_GAP_STRONGER_ELECTRONIC_REPRESENTATION_REQUIRED
selected_configuration = null
```

Это означает недостаточность executed representations, а не ложность какой-либо известной конфигурации.

## 56. Переход обратно в общий Φ-space

Representation gap формируется как digest-bound evidence и передаётся в
`ADAPTIVE-RESEARCH-KERNEL/15.4.0`:

```text
representation_gap = true
gap_kind = ELECTRONIC_REPRESENTATION_RESPONSE_GAP
blind_no_named_law_catalog = true
operator_probe_rows = []
```

Если независимых operator-response observations ещё нет, общий kernel обязан остановиться на response-free discriminating protocol. Он не имеет права заполнить ответы текстовым ИИ или выбрать известный named solver.

## 57. Epistemic boundary электронного owner

Даже status

```text
PROVISIONAL_GROUND_STATE_WITHIN_EXECUTED_REPRESENTATIONS
```

означает только minimum внутри исполненного множества representations. В 15.4.0 owner всегда держит

```text
scientific_ground_state_established = false
```

до независимого evidence/promotion procedure. Для сложных атомов instability является валидным научным результатом и должна расширять representation space.

# XXII. Evidence-Born Many-Body Operator Coordinates — 15.4.0

## 58. Почему следующий шаг не является «добавить MCDHF»

Electronic state-space owner 15.3 обнаруживал representation gaps, но сам факт такого gap ещё не определяет, какая новая many-electron representation необходима. Поэтому current owner запрещает переход

```text
REPRESENTATION_GAP -> SELECT_KNOWN_METHOD("CI/MCDHF/FSCC/...")
```

как научное доказательство. Вместо этого общий `ADAPTIVE-RESEARCH-KERNEL/15.4.0` получает digest-bound residual evidence и должен определить, каких **операторных координат** не хватает существующему representation language.

В 15.4.0 это реализовано через конечномерный fermionic research carrier и black-box operator action. Это не замена open-ended Φ-space конечным базисом: finite carrier является только исполнимым различающим экспериментом и может расширяться отдельным lifecycle/probe step.

## 59. Fermionic carrier

Для числа электронов `N` и текущего числа spin-orbitals `M` вводится fixed-particle carrier

\[
\mathcal F_{N,M}
=
\operatorname{span}\{|I\rangle:\ I\subset\{1,\ldots,M\},\ |I|=N\}.
\]

Его размерность

\[
D_{N,M}=\binom{M}{N}.
\]

Базисный determinant кодируется occupation bit pattern. Fermionic creation/annihilation operators реализуют антикоммутационные знаки напрямую:

\[
a_p a_q^\dagger+a_q^\dagger a_p=\delta_{pq},
\qquad
\{a_p,a_q\}=\{a_p^\dagger,a_q^\dagger\}=0.
\]

`M` в конкретном execution не является физическим orbital ceiling. Если текущий carrier недостаточен, допустимый результат — запрос его расширения, а не утверждение о границе атомной физики.

## 60. Open interaction-rank grammar

Candidate representation строится не из списка named methods, а из number-conserving normal-ordered monomials. Для joint-coordinate arity `k`:

\[
\hat O^{(k)}
=
\sum_{|A|=|B|=k}
 c_{AB}\,
 a^\dagger_{a_1}\cdots a^\dagger_{a_k}
 a_{b_k}\cdots a_{b_1}.
\]

Для real Hermitian executable carrier используются диагональные monomials и симметризованные пары

\[
\hat T_{AB}^{(+)}
=
\hat T_{AB}+\hat T_{BA}.
\]

Grammar образует возрастающую последовательность shells

\[
\mathcal G_1\subseteq \mathcal G_2\subseteq\cdots,
\]

где `k=1` описывает one-coordinate operator action, `k=2` разрешает joint action двух fermionic coordinates и т. д. В контракте:

```text
search_starts_at_rank = 1
fixed_global_interaction_rank_ceiling = null
known_many_body_method_required = false
named_solver_selection = false
```

Конечный fixed-N carrier имеет локальный algebraic maximum `k<=N`; этот факт относится только к текущему carrier и **не** превращается в global physics ceiling.

## 61. Response-free probe freeze

`MANY-BODY-OPERATOR-PROBE-DESIGN/1.0.0` получает только:

```text
freeze_digest
N
M
current interaction-rank shell
```

и строит probe states

\[
x_p\in\mathcal F_{N,M}
\]

до получения каких-либо operator responses. Discovery и sealed holdout identities фиксируются заранее:

\[
\mathcal P=\mathcal P_{disc}\sqcup\mathcal P_{hold}.
\]

Probe selector выбирает состояния, повышающие rank feature matrix текущей generic grammar. Он не читает ground-state configuration, atomic table, Coulomb integrals или named many-body algorithm.

После freeze независимый world owner может вернуть только black-box action

\[
y_p=\hat H x_p.
\]

Синтезатор видит пары `(x_p,y_p)` и carrier metadata, но не внутреннее построение `H`.

## 62. Discovery / sealed-holdout fit

Для shell `k` строится operator dictionary

\[
\{G^{(k)}_1,\ldots,G^{(k)}_{m_k}\}.
\]

На discovery rows коэффициенты находятся из linear least-squares operator action:

\[
\hat H_k
=
\sum_j c_jG^{(k)}_j,
\qquad
c_*=\arg\min_c
\sum_{p\in\mathcal P_{disc}}
\left\|
 y_p-\sum_jc_jG_jx_p
\right\|_2^2.
\]

Sealed holdout не участвует в выборе coefficients/terms. Его gate:

\[
\operatorname{NRMSE}_{hold}(k)
=
\frac{
\sqrt{\frac1Q\sum_{p\in\mathcal P_{hold}}\|y_p-\hat H_kx_p\|_2^2}
}{
\max\left(
\sqrt{\frac1Q\sum_{p\in\mathcal P_{hold}}\|y_p\|_2^2},
10^{-15}
\right)
}.
\]

Shell квалифицируется только если

\[
\operatorname{NRMSE}_{hold}(k)\le\varepsilon_{fit}.
\]

Если shell `k` провален, Adaptive Research Kernel может открыть `k+1`. Если первый прошедший shell имеет `k>1`, рождается research-local coordinate

```text
axis_id = operator_interaction_rank
origin = SEALED_BLACK_BOX_OPERATOR_RESIDUAL
value = k
canonical = false
activation_state = RESEARCH_LOCAL_ACTIVE
```

Её смысл: **минимальная joint-coordinate arity, необходимая для текущего frozen carrier/response experiment**, а не фундаментальная константа природы.

## 63. Independent atomic many-body reference world

Чтобы проверить сам механизм без подстановки published atomic answers, используется явно маркированный owner

```text
ATOMIC-MANY-BODY-REFERENCE-WORLD/1.0.0
```

Это deterministic reference simulation, не empirical measurement. Его скрытая benchmark model в текущем experiment:

\[
\hat H
=
\sum_i\left(-\frac12\nabla_i^2-\frac{Z}{r_i}\right)
+
\sum_{i<j}\frac1{r_{ij}},
\]

ограниченная небольшим hydrogenic `s`-orbital research basis. Для spherically averaged `s` functions electron-electron radial kernel после углового интегрирования использует

\[
\frac1{r_>} = \frac1{\max(r_1,r_2)}.
\]

Одночастичные и двухчастичные integrals формируют hidden determinant-space Hamiltonian. Эти integrals, Coulomb kernel и Hamiltonian matrix **не передаются** synthesis owner; в postfreeze receipt публикуются только audit digests/diagnostics.

Поэтому текущий benchmark проверяет способность Atlas восстановить operator interaction structure по black-box action, а не способность вспомнить Hamiltonian из входа.

## 64. Blind experiment: negative control → discovery → transfer

Current freeze:

```text
negative control: Z=1
interaction-rank discovery: Z=2
blind transfer: Z=3,4
neutral count rule: N=Z
initial spatial research orbitals: 3
blind rank adaptation after response: forbidden
fit tolerance: 1e-8
```

Freeze digest current execution:

```text
3e979f21815172ac26c5ffe077dd4df92870146dce0b4d70574b15101edbbf94
```

### Negative control

Для `Z=1`, `N=1` one-body shell обязан быть достаточен. Получено

\[
\operatorname{NRMSE}_{hold}^{Z=1,k=1}
=2.93\times10^{-15},
\]

то есть PASS. Это отрицательный контроль против механизма «всегда открывать higher rank».

### Discovery atom

Для `Z=2` отдельный rank-one screen дал

\[
\operatorname{NRMSE}_{hold}^{k=1}
\approx1.2568\times10^{-1},
\]

FAIL. Внутри Adaptive Research Kernel независимый replay rank-one shell также провалился:

\[
\operatorname{NRMSE}_{hold}(1)
\approx1.1912\times10^{-1}.
\]

После открытия следующего interaction shell:

\[
\operatorname{NRMSE}_{hold}(2)
\approx2.29\times10^{-15},
\]

PASS. Поэтому born research-local coordinate текущего benchmark:

\[
\boxed{k_{born}=2}.
\]

При этом `UnknownUnknownRepresentationOwner` получает не слово «CI» или «MCDHF», а obligation вида

```text
joint_coordinate_interaction(arity=2)
```

с причиной `minimal normal-ordered operator shell required by sealed black-box holdout`.

## 65. Blind precommit falsification

После discovery значение `k=2` фиксируется **до** получения responses blind atoms. Для blind receipt разрешён ровно precommitted shell; response не может открыть `k=3` и тем самым спасти гипотезу post hoc.

Получено:

\[
Z=3:\quad
\operatorname{NRMSE}_{hold}(k=2)
\approx2.07\times10^{-15},
\]

\[
Z=4:\quad
\operatorname{NRMSE}_{hold}(k=2)
\approx2.28\times10^{-15}.
\]

В обоих receipts:

```text
PRECOMMITTED_MANY_BODY_OPERATOR_COORDINATE_VALIDATED_NOT_LAW
probe_design_history_length = 1
blind_precommitted_rank_may_adapt_after_holdout = false
```

Следовательно discovery не использует blind atom identity/response для выбора rank, а blind run не может переобучить structural coordinate после раскрытия результата.

## 66. Что именно доказал текущий experiment

Доказано на reproducible reference benchmark:

1. one-coordinate grammar не всегда достаточна;
2. insufficiency обнаруживается sealed operator residual, а не таблицей исключений;
3. general Adaptive Research Kernel умеет открыть следующий operator-arity shell;
4. research-local coordinate `operator_interaction_rank=2` рождается из evidence;
5. precommitted coordinate переносится на два unseen reference atoms без post-response adaptation;
6. named many-body method не выбирается как ответ.

Не доказано:

```text
complete atomic correlation representation
complete physical orbital basis
physical ground-state energies of H/He/Li/Be
MCDHF or CI equivalence
universal physical interaction rank = 2
periodic-table completion
post-118 element existence
scientific many-body law
```

Текущий reference basis намеренно мал и s-only; его абсолютные energies являются только sanity diagnostics внутренней simulation. Они не используются как truth gate. Для научного atomic solver дальнейшая representation evolution должна включить basis/angular/spin-relativistic/correlation coordinates и пройти независимые physical-world / high-precision benchmark gates без подстановки answer-bearing configurations.

## 67. Следующий frontier

После структурного рождения `joint_coordinate_interaction` следующий честный вопрос уже не «добавить известный solver», а:

\[
\boxed{
\text{какие basis/operator coordinates необходимы, чтобы одновременно закрыть}
\begin{cases}
\text{atomic energies},\\
\text{level ordering},\\
\text{response observables},\\
\text{relativistic splitting}
\end{cases}
\text{на blind holdout?}
}
\]

Если текущий fermionic carrier теряет identifiability, Atlas должен расширить carrier/basis через lifecycle evidence. Если operator grammar недостаточна — открыть следующий arity/representation shell. Если reference simulation расходится с world evidence — reference model не продвигается, а получает falsification receipt.

## 68. Transactional current replay is not a scientific ceiling

The current release separates scientific search semantics from runtime test orchestration. Let the dynamically collected current test inventory be

\[
\mathcal T=\{t_1,\ldots,t_m\}.
\]

Before execution, the ordered inventory and its partition are frozen into a digest-bound replay plan

\[
P=\operatorname{Freeze}\!\left(\mathcal T,\;B\right),
\]

where `B` is a finite **runtime isolation batch size**. Each batch is executed in a fresh process. The final aggregate gate is

\[
\operatorname{PASS}_{replay}
\iff
\left(\bigcup_j \mathcal T_j=\mathcal T\right)
\land
\left(\mathcal T_i\cap\mathcal T_j=\varnothing\right)_{i\ne j}
\land
\bigwedge_{t\in\mathcal T}\operatorname{PASS}(t).
\]

The aggregator also recollects the current inventory and requires exact equality with the frozen inventory. Therefore partitioning cannot remove a failing node or silently change the acceptance surface.

The parameters

```text
max_nodes_per_surface
surface_timeout_seconds
```

are process-isolation/safety controls. They are explicitly **not** limits on the scientific law space, operator interaction rank, axis count, atomic Z/N frontier, hypothesis complexity, or truth criteria.

Current release receipt:

\[
\boxed{49/49\ \text{current test nodes PASS}}
\]

with five digest-bound fresh-process batch receipts covering the exact frozen inventory.

# XXIV. Persistent Multidimensional Law Atlas — CURRENT 15.10.1

## XXIV.1 Canonical object

Atlas stores scientific coordinates rather than a disposable per-problem feature list. Let \(\mathcal A_t\) denote the canonical coordinate atlas after research state \(t\). The monotone persistence requirement is

\[
\boxed{\mathcal A_{t+1}=\mathcal A_t\cup\Delta\mathcal A_t},
\]

subject to admission/provenance rules for \(\Delta\mathcal A_t\). Canonical axes are not erased merely because a later study does not activate them. For a study \(S\),

\[
\mathcal A_t=\mathcal A^{\rm active}_S\cup\mathcal A^{\rm dormant}_S,
\qquad
\mathcal A^{\rm active}_S\cap\mathcal A^{\rm dormant}_S=\varnothing.
\]

`dormant` therefore means *not currently activated by evidence*, not *forgotten*.

The authoritative owner for general typed law-space search is

```text
ATLAS-LAW-SPACE-SEARCH/1.0.0
```

while `SCIENTIFIC-AXIS-SPACE/1.0.0` is only a compatibility adapter.

## XXIV.2 Domain typing and metrology

Each observed quantity \(q_i\) is represented by a typed descriptor

\[
Q_i=(D_i,\tau_i,s_i,c_i,r_i,\ldots),
\]

where \(D_i\) is a metrology/dimension vector, \(\tau_i\) is the quantity kind, and the optional state/component/reference fields identify scientifically meaningful relations. The benchmark or domain adapter may bind labels to such descriptors, but it does not select the target law.

For an observable \(y\), a dimensionally admissible scale \(s\) satisfies

\[
D(s)=D(y),
\]

and a dimensionless invariant \(\pi\) satisfies

\[
D(\pi)=0.
\]

A metrology contradiction is a first-class gap. It is not silently repaired from knowledge of the hidden target equation.

## XXIV.3 Reusable canonical coordinate archetypes

The physics registry now contains reusable coordinate archetypes that were previously research-local procedural knowledge. Examples include

\[
\Delta q=q_2-q_1,
\qquad q_1+q_2,
\qquad q_2/q_1,
\]

\[
r^2=\sum_k(x_{2k}-x_{1k})^2,
\qquad r=\sqrt{r^2},
\qquad a\cdot b=\sum_k a_kb_k,
\]

\[
E_T=k_BT,
\qquad \beta=v/c,
\qquad \chi_{12}=u v/c^2,
\qquad \phi=\omega t,
\]

plus weighted-state means, detuning/action phases, thermal-quantum ratios, resonance coordinates, direction cosines, coherent cross magnitude and superposition intensity, periodic response and evidence-born response coordinates.

These objects are **coordinate classes**, not answer-bearing formulas. A law hypothesis may use them, combine them or reject them.

## XXIV.4 Owner-connected search and axis birth

For observations \(\mathcal O\), the owner explores a qualified region of the accumulated Atlas,

\[
R_S\subseteq\bigcup_{k\ge1}\mathcal A_t^k,
\]

rather than a fixed expression-tree grammar. Search begins with lower-complexity owner-connected coordinate sets and may open the next joint-axis shell only after residual evidence shows the current region inadequate. The current shell is an execution state, not a universal order ceiling.

A provisional relation has the general projection form

\[
\hat y=\sum_{j\in J}c_j a_j(x),\qquad a_j\in R_S,
\]

but this algebraic representation is an evaluator of a relation hypothesis; it does not redefine Atlas as symbolic regression. The selector is rank-aware and must validate the actual residual to avoid false cancellation among nearly collinear coordinates.

If the selected relation leaves structured residual \(r=y-\hat y\), the next action may be

\[
r\Rightarrow
\begin{cases}
\text{activate a dormant coordinate},\\
\text{birth a research-local coordinate},\\
\text{open a higher joint-axis shell},\\
\text{change representation},\\
\text{design a discriminating experiment},\\
\text{return UNKNOWN/GAP}.
\end{cases}
\]

Novel axes pass through `DYNAMIC-AXIS-ADMISSION/6.24.0` and `DYNAMIC-AXIS-PROMOTION/8.0.0`; a relation passes through `SCIENTIFIC-PROMOTION-CORE/9.0.0`. `ATLAS-LAW-SPACE-SEARCH/1.0.0` itself does not auto-promote a law.

## XXIV.5 Persistence and cross-domain reuse

A promoted coordinate remains addressable in later studies. Domain registries preserve domain semantics while typed bridges may form qualified cross-domain relations without collapsing the source registries. Thus an axis discovered in one context can later be dormant, reactivated, combined with another domain coordinate, or used to design a new experiment.

The architectural invariant is therefore

\[
\boxed{\text{not used now}\neq\text{deleted from Atlas}.}
\]

This is the central distinction between Atlas and a one-shot solver.

## XXIV.6 Clean-baseline persistence boundary

The shipped 15.6.1 state preserves the coordinate system and static source knowledge but sets generated research state to the empty state: $H_{generated}=\varnothing$, $E_{generated}=\varnothing$, generated frontier/search ledgers $=\varnothing$. This is a storage-state reset, not a deletion of canonical axes.

## XXIV.8 Current invariant summary

```text
canonical axes persist across studies
dormant != forgotten
benchmark label semantics do not belong to ATLAS-LAW-SPACE-SEARCH
SCIENTIFIC-AXIS-SPACE is compatibility-only
new reusable coordinates enter common axis lifecycle
relation hypothesis is not automatically a law
old domain owners remain live
fixed global axis/order ceiling = null
expression tree is not the primary Atlas search object
```


# XXV. Clean research state model — 15.6.1

Define persistent baseline $B=(\mathcal A^{canonical},\mathcal K_{source},\mathcal Q,\mathcal C,\mathcal M)$ and mutable research state $R=(\mathcal H,\mathcal E,\mathcal F,\mathcal P,\mathcal G)$. The cleanup operator is

\[\mathcal C_{reset}(B,R)=(B,\varnothing).\]

It is required to preserve canonical axes, typed quantities/constants, source-law passports, archetypes, computational-method definitions and raw/source snapshots. It must delete generated candidates, evidence, frontier/search products, frozen/post-freeze receipts, generated routes and calculation reports. Therefore cleanup changes state, not the scientific coordinate basis.


# XXVI. First post-clean Atlas-native blind interaction experiment — 15.7.0

Let the current research representation be

\[
\mathcal R_0=(y; x; z_{dormant}),
\]

where \(x\) is the only active predictor and \(z\) is observable but unavailable to hypothesis synthesis until residual evidence activates it. The initial fair-dovetail shell therefore searches \(\mathcal H(x)\), not \(\mathcal H(x,z)\).

The initial survivor candidate has the affine form

\[
\hat y_0=c_0+c_1x,
\]

with held-out normalized error

\[
\operatorname{NRMSE}_0=0.4215528718826227.
\]

Residuals \(r_i=y_i-\hat y_{0,i}\) are passed to the existing residual-axis discovery owner. The dormant coordinate \(z\) is selected as structured residual context; only after this event does the representation evolve to

\[
\mathcal R_1=(y;x,z).
\]

The same complexity shell then contains sparse degree-two interaction charts and the best generated candidate is

\[
\boxed{\hat y_1=c_0+c_1x+c_2xz}.
\]

For the deterministic controlled world the fitted parameters are

\[
(c_0,c_1,c_2)=(0.7,1.1999999999999988,0.4499999999999999),
\]

with internal post-activation holdout

\[
\operatorname{NRMSE}_{internal}=7.74807359970427\times10^{-16}
\]

and independent sealed holdout

\[
\operatorname{NRMSE}_{sealed}=7.846977229612316\times10^{-16}.
\]

Thus the measured improvement is effectively unity:

\[
1-\frac{\operatorname{NRMSE}_{internal}}{\operatorname{NRMSE}_0}\approx 1.
\]

The key architectural statement is not the particular polynomial. It is the transition

\[
\boxed{z\in DORMANT\_AVAILABLE\_AXIS\;\not\Rightarrow\;z\in\mathcal H}
\]

followed by

\[
\boxed{I(r;z)>0\;\Rightarrow\;\text{residual-driven activation}\;\Rightarrow\;\mathcal H(x,z)}.
\]

The hidden relation used to synthesize the control world is confined to the fixture generator and final verification gate and is absent from the request delivered to `AdaptiveResearchKernelOwner.advance`. Consequently the receipt demonstrates a post-clean Atlas execution and representation evolution. It does not constitute scientific promotion or a law of nature.


# XXVII. First blind real-scientific experiment — 15.8.0

The real-data residual model starts from a low-capacity baseline on observed coordinates. The generated local coordinate is

```math
g(f;f_0,w)=\exp\left[-\frac12\left(\frac{f-f_0}{w}\right)^2\right].
```

`f_0,w` are selected from training regimes only. For held-out regime `U=40 m/s`,

```math
RMSE_0=3.2047739558322985,\qquad RMSE_1=0.9566362672392704,
```

so

```math
I=\frac{RMSE_0-RMSE_1}{RMSE_0}=0.7014964922882287.
```

The frozen discovery gives `f_0=9.0 Hz`. Only after freeze, independent reconciliation opens the stored flexible-mode descriptor `f_flex=9.0 Hz`, hence `|f_0-f_flex|=0`. This converts the interpretation from provisional new-axis language to rediscovery of an existing physical coordinate. No canonical promotion follows from this receipt alone.



# XXVIII. Atlas-wide frontier candidate scan — 15.9.0

## XXVIII.1 Research object

Release 15.9.0 separates the preserved baseline registries from the active research frontier. The baseline candidate and evidence registries remain empty, while the current candidate ledger is an explicit research-state object:

```math
\mathcal C_{15.9}=\mathcal C_{pair}\cup\mathcal C_{alg}\cup\mathcal C_{op}\cup\mathcal C_{real}\cup\mathcal C_{axis}.
```

For the sealed scan,

```math
|\mathcal C_{pair}|=256,\quad |\mathcal C_{alg}|=156,\quad |\mathcal C_{op}|=11,\quad |\mathcal C_{real}|=5,\quad |\mathcal C_{axis}|=1,
```

hence

```math
\boxed{|\mathcal C_{15.9}|=429}.
```

Algebraic identity is quotiented by non-zero global scalar/sign through a canonical primitive expanded polynomial representation before candidate IDs are assigned. This removes representation-only duplicates without falsifying or discarding a distinct mathematical relation.

Historical 15.9.0 note: The count `429` is the number of **materialized candidate records in this execution**, not a bound on the candidate space.

## XXVIII.2 Candidate preservation law

The research ledger obeys

```math
\forall c\in\mathcal C_{15.9}: Active(c)=1.
```

Absence of a novelty proof is not falsification:

```math
\neg NoveltyProven(c)\not\Rightarrow False(c).
```

A known overlap also does not imply deletion:

```math
KnownOverlap(c)\not\Rightarrow Delete(c).
```

Similarly, ranking is an attention operator `R`, not a projection that changes membership:

```math
R:\mathcal C\to\mathbb R,\qquad \mathcal C_{after\ ranking}=\mathcal C_{before\ ranking}.
```

This corrects the previous `top-N` reporting behavior: top views may summarize a frontier, but every generated materialized candidate remains content-addressed in the full ledger.

## XXVIII.3 Cross-domain void geometry

For the current 655 canonical axes, Atlas scans every pair whose two axes belong to different registered domains. The exact executed set has

```math
|\mathcal P_{cross-domain}|=183996.
```

The pair space is partitioned into a materialized attention surface and an open addressable remainder:

```math
\mathcal P_{cross-domain}=\mathcal P_{materialized}\sqcup\mathcal P_{open},
```

with

```math
|\mathcal P_{materialized}|=256,\qquad |\mathcal P_{open}|=183740.
```

No logical negation follows from non-materialization:

```math
p\in\mathcal P_{open}\not\Rightarrow Rejected(p),\qquad p\in\mathcal P_{open}\not\Rightarrow Falsified(p).
```

High-density materialized cross-domain regions include aeronautics↔physics, physics↔quantum/computational methods, chemistry↔physics, pharmaceutical↔physics, mechanics↔physics, mathematics↔physics and materials↔physics. These pair-frontier records are launch coordinates for research, not evidence by themselves.

Examples with both source-owner binding and a registered bridge include measurement-model overlap between metrology and physics, observable-type overlap between aeronautics and physics, stability overlap between mathematics and mechanics, stability-condition overlap between chemistry and mathematics, and composition overlap between chemistry and materials science.

## XXVIII.4 Algebraic source-derived frontier

Historical 15.9.0 execution note: The authoritative unknown-frontier owner derives consequences from source-law relations without reading a hidden target formula or the current materialized-law catalogue during generation. In the sealed execution it generated 156 candidates and stopped at

```text
EXECUTION_BUDGET_MAX_RESULTANT_EVALUATIONS
```

after 260 resultant evaluations. This stop is an execution frontier:

```math
BudgetStop\not\Rightarrow ScientificOrderCeiling.
```

Representative source-minimal generated relations are

```math
2C_D\Delta_nWq-DK_gU_{de}Va_{lift}\rho=0,
```

from discrete-gust load, drag and wing-loading source owners;

```math
Range\,c_T\left(2\Delta_ncw-K_gRe\,U_{de}a_{lift}\mu\right)=0,
```

from Breguet range, discrete-gust load and Reynolds-definition owners; and

```math
V\rho(C_DL-C_LD)=0,
```

from drag, dynamic-pressure and lift owners.

Their status is `CANDIDATE_SOURCE_DERIVED` plus `CANDIDATE_CURRENT_CORPUS_UNMATERIALIZED`; that means the relation is not materialized in the current Atlas corpus under the executed derivation, **not** that it is new to world science.

## XXVIII.5 Operator-composition frontier

The operator owner generated 11 candidates and exhausted the currently executable declared operator regions. Eight are current-corpus-unmaterialized. Retained examples include

```math
\rho D_tu=\nabla\cdot\left[\int_0^t G(t-s):\varepsilon(s)\,ds\right]+\rho b,
```

for continuum momentum with viscoelastic memory,

```math
\partial_tc_i=-\nabla\cdot\left(-D_i\nabla c_i-z_iu_iFc_i\nabla\phi+c_iv\right)+R_i,
```

for electrodiffusion-reaction balance, and

```math
\partial_tc=\nabla\cdot\left(M\nabla\left(\frac{\partial f}{\partial c}-\kappa\nabla^2c\right)\right),
```

for a high-order phase-field chart.

These compositions remain candidates until operator quantity/tensor dimensions, validity-chart overlap and external novelty are audited. Three aeronautics operator candidates are marked partially explained because the same source set already has a materialized closure; partial explanation still does not delete them.

## XXVIII.6 Real-data mechanism competition

Five DLR gust-response mechanisms remain simultaneously active:

```text
H-AERO-REAL-001  GUST_INPUT_SCALAR_CALIBRATION
H-AERO-REAL-002  GUST_FIELD_FREQUENCY_SHAPE
H-AERO-REAL-003  FIRST_MODE_PARTICIPATION_CORRECTION
H-AERO-REAL-004  UNSTEADY_MEMORY_ZERO_POLE
H-AERO-REAL-005  STRUCTURAL_POLE_SHIFT_DAMPING
```

After two frozen holdouts their retrospective normalized weights are

```math
(0.1123770,\ 0.2059900,\ 0.1206324,\ 0.1858415,\ 0.3751591)
```

in ID order `001...005`. This ordering is not a proof of causal identity. The current evidence explicitly has

```text
unique_mechanism_identified = false.
```

The most experimentally actionable born coordinate is the provisional measurable transfer magnitude

```text
gust_probe_to_wing_transfer_magnitude
```

and the next discriminator targets the complex transfer

```math
\boxed{G_{probe\to wing}(f,U)=\frac{w_{wing}(f,U)}{w_{probe}(f,U)}}.
```

Required measurements are synchronized upstream and near-wing gust field, WRBM magnitude and phase, distributed structural response, independent modal frequency/damping, measured actuator position when active, multiple gust frequencies, at least two freestream speeds and repeats for uncertainty.

This experiment can distinguish three live mechanisms: gust-field transfer, unsteady aerodynamic memory and operating-condition structural pole/damping shift.

### XXVIII.6.1 Executed discriminator and real-data identifiability gate

The existing authoritative phase/speed/modal discriminator was executed rather than replaced. Its primary object is

```math
G_{pw}(f,U)=\frac{W_{wing}(f,U)}{W_{probe}(f,U)},
```

with geometric convection phase removed before testing scalar calibration versus a dynamic gust-field transfer. Independent free-decay/modal records are required for the structural branch, so the load residual cannot be reused to manufacture a modal explanation.

The method passes five pure-family qualification scenarios and explicit null, mixed-H4/H5 and OOD controls. Current public real evidence, however, supplies only multi-speed WRBM magnitude. It does not supply the synchronized complex channels required to evaluate `G_pw` or the same-test independent modal series. Hence

```text
full_real_complex_discriminator = BLOCKED
posterior_update_allowed        = false
physical_measurement_status     = DATA_PENDING
```

This is an identifiability result, not a negative scientific result. The candidates remain active and the born axis retains `CANDIDATE_EXPERIMENT_DESIGNED` plus `CANDIDATE_REAL_DATA_PENDING`.

## XXVIII.7 Open frontiers and epistemic boundary

The neutrino full open-ended real-data owner was invoked during the research pass but did not complete a full execution within the controlled run. No reduced/truncated substitute is recorded as a complete neutrino scan. Therefore

```text
NEUTRINO_FULL_OPEN_ENDED_REALDATA = NOT_MATERIALIZED_IN_THIS_SCAN
```

and the region remains open.

The 15.9.0 scan establishes **where that sealed execution generated research candidates** and preserves them for falsification. It does not establish that any of the 429 records is a new law of nature. Domain labels are interpretation metadata after candidate birth; cross-domain coordinates are not forced into a single discipline before evidence warrants it.


# XXIX. Low-frequency gust anomaly and causal discriminator — 15.10.1

The 15.10.1 research cycle does not add another scientific solver. It extends the existing `CONSTRAINT-ATLAS` owner with a public-evidence analysis of the unresolved oLAF gust-load mismatch already preserved in the Atlas frontier.

## XXIX.1 Observable residual

For Figure 16 define

\[
\delta_G(f)=M_{\rm sim}^{\rm WRBM}(f)-M_{\rm exp}^{\rm WRBM}(f).
\]

The preserved vector-digitized values produce

\[
\bar\delta_G^{4:8}=1.7612432509816798\ {\rm dB},\qquad
\delta_G(9)=-0.11918791925720029\ {\rm dB},
\]

and

\[
\bar\delta_G^{10:12}=0.35270650973494827\ {\rm dB}.
\]

Thus the residual is strongly band-dependent rather than a uniform offset.

## XXIX.2 Conditional effective-input coordinate

Only as a diagnostic conditional attribution, if the complete output residual were assigned upstream of the nominal wing-load model,

\[
|G_{\rm eff}(f)|=10^{-\delta_G(f)/20}.
\]

For 4–8 Hz,

\[
\overline{|G_{\rm eff}|}=0.8165672757732683,
\]

with the individual values spanning approximately `0.8043…0.8381`. This quantity is **not** an observed probe→wing transfer and must not be promoted into the canonical axis registry until independently measured.

## XXIX.3 Independent channel negative control

Let

\[
\delta_F(f)=M_{\rm sim}^{\rm flap\to WRBM}(f)-M_{\rm exp}^{\rm flap\to WRBM}(f).
\]

The flap channel uses the same load output but a different excitation path. The source paper describes the corresponding experiment/simulation agreement as almost perfect through the 12 Hz sweep. Atlas therefore stores this channel as a negative control against the hypothesis that every Figure-16 discrepancy can be assigned automatically to a universal structural/output-chain error. The digitized trace is not a raw uncertainty model, so H005 is not falsified.

## XXIX.4 Multi-speed scalar-gain shape test

For each public speed panel define the normalized open-loop spectrum

\[
S_U(f)=M_U(f)-M_U(9\,{\rm Hz}).
\]

If the only speed-dependent discrepancy were a frequency-independent scalar calibration, then

\[
S_{U_1}(f)=S_{U_2}(f)
\]

for common frequencies. The public Figure-23 digitizations do not have this property. For 30 and 50 m/s the common-frequency normalized-shape RMSE is

\[
3.7083993376\ {\rm dB},
\]

and the maximum absolute difference is

\[
5.3482\ {\rm dB}.
\]

Because digitization uncertainty is not published, this creates `TENSIONED_AS_COMPLETE_EXPLANATION` for H001 rather than a falsification label.

## XXIX.5 Three-state causal decomposition

The decisive experiment is

\[
G_{p\to e}(f,U)=\frac{W_{\rm encounter}(f,U)}{W_{\rm probe}(f,U)}.
\]

Three physical states are required:

\[
G^{(0)}=G_{\rm NO\ WING},\qquad
G^{(r)}=G_{\rm RIGID},\qquad
G^{(f)}=G_{\rm FLEXIBLE}.
\]

Then the mechanism partition is observationally defined by

\[
\Delta G_{\rm aero}=G^{(r)}-G^{(0)},
\qquad
\Delta G_{\rm aeroelastic}=G^{(f)}-G^{(r)}.
\]

`NO WING` isolates generator/tunnel transport. `RIGID−NO WING` isolates modification of the gust field by aerodynamic wing presence. `FLEXIBLE−RIGID` isolates incremental aeroelastic feedback. Synchronized upstream and encounter-plane flow, WRBM and modal channels are mandatory.

## XXIX.6 Epistemic state

The public anomaly is reproduced and quantified. No unique mechanism, new law, or world novelty is claimed. H001–H005 remain candidates until explicit declared falsification gates are executed. The canonical common scientific rules remain owned by `COMMON-SCIENTIFIC-RULES/1.0.0`; this chapter adds only domain-specific observables and discriminators.


# XXX. Integration and reproducibility repair — 15.10.1

The 15.10.1 repair **regenerates** the active scientific frontier rather than preserving the old budget-truncated 15.10.0 ledger cardinality. The qualification model distinguishes three disjoint sets: static source knowledge $K$, archived provenance $H$, and the active unresolved frontier $F$. The historical $2771$ control-anchor count belongs to $H$, not to the active candidate registry. The invariant is $H\cap F=\varnothing$ and archival provenance cannot satisfy a current scientific gate.

For the regenerated 15.10.1 state,

```math
|F|=256+6+116+11+5+1=395.
```

The six higher-order records are produced by the existing owner-connected directed-research engine, not by fixed witness tuples. Their active axis orders are data/registry determined (current maximum `324`), with no fixed axis-order or owner-visit scientific ceiling. The algebraic branch partitions the 18 current polynomial source relations into three connected components and computes deterministic Gröbner bases. Its finite current-source closure is

```math
I_j=\langle f_i:i\in C_j\rangle,\qquad G_j=\operatorname{Groebner}(I_j),
```

with 116 canonical basis consequences overall. Termination `ALGEBRAIC_IDEAL_BASIS_SATURATED` means closure of the **current polynomial ideals only**; it is not closure of future axes, representations, source laws, non-polynomial carriers or owner-connected regions.

Replay evidence uses a canonical receipt digest $D=H(\mathrm{test\ identity},\mathrm{return\ code},\mathrm{pass\ count},\mathrm{plan\ digest},\mathrm{claim\ boundary})$; volatile wall-clock text is diagnostic only and is excluded from $D$. Two independent 59-node fresh-process replays produced identical plan and result identities: $D_{plan}=\texttt{9444f9831d2e5e00c7c084208ba96d4a8b15bcf420d325317df0b5543efb9e89}$ and $D_{replay}=\texttt{420d821f1e41b5377d3c7bbd9031801d12ce93c9d0ace51b614d2f71f809a26a}$. All 30 canonical batch digests agreed; runtime duration remains explicitly noncanonical. The seal is closed-world: the actual distributable file set must equal the declared controlled set plus the three self-referential release-envelope files.
\n\n# XXXI. Restored resident cognitive dynamics — 15.10.2\n\n15.10.2 does not replace the scientific search space by an expression-tree AI. It restores the previously implemented cognitive layer over the same owner/axis/evidence graph. Let the mutable resident state at heartbeat $t$ be\n\n\[\nS_t=(M_t,C_t,G_t,P_t,K_t,O_t,W_t,\Theta_t,\Sigma_t),\n\]\n\nwhere $M_t$ is epistemic memory, $C_t$ grounded concepts, $G_t$ goals, $P_t$ plans, $K_t$ reusable skills, $O_t$ qualified composed operators, $W_t$ post-freeze world-action experience, $\Theta_t$ learned world-action models and $\Sigma_t$ the self-model/capability state. A resident heartbeat is a constrained transition\n\n\[\nS_{t+1}=\mathcal T_\Phi(S_t,E_t;\,\mathcal A,\mathcal O,\mathcal B),\n\]\n\nwith current axis registry $\mathcal A$, executable owners $\mathcal O$, and claim boundary $\mathcal B$. $\mathcal T_\Phi$ may update memory, concepts, goals, plans, skills and learned action models, but it has no transition that directly sets scientific truth. Scientific promotion remains owner/evidence gated.\n\nThe live capability ledger is reconstructed from the executable release rather than read from a historical capability snapshot:\n\n\[\nL_{cap}=\mathcal L(\text{owners},\text{APIs},\text{registries},\text{qualifications},\text{claim boundary}).\n\]\n\nFor 15.10.2, $|L_{cap}|=285$ executable/qualified capabilities and $|\mathcal A|=655$. The unresolved architectural obligation `COLLECTIVE_COORDINATION` remains explicit; an absent capability is therefore represented as an obligation/GAP rather than silently treated as impossible.\n\nWorld-action learning uses only admitted post-freeze experience. For action $a$, hypothesis $h$ and supported context $x$, the resident model estimates predictive observation probabilities\n\n\[\n\hat p(o\mid h,a,x;D_{post})\n\]\n\nfrom $D_{post}$, evaluates held-out calibration against competing model families, separates operational epistemic/aleatoric uncertainty, rejects unsupported OOD contexts and can demote a model after replicated drift. Learned likelihoods are inputs to action-selection/EIG; they are not supplied as benchmark truth and do not imply a scientific law.\n\nThe controlled wake artifact contains 240 admitted post-freeze experiences and one calibrated model. The selected next internal research action was\n\n\[\na^*=\texttt{MEASURE::systems\_control.causal\_inference}.\n\]\n\nBoth subsequent autonomous cycles returned `AUTONOMOUS_RESEARCH_GAP_INDEPENDENT_EVIDENCE_REQUIRED`, so the transition law satisfies the fail-closed condition\n\n\[\nE_{independent}=\varnothing\quad\Longrightarrow\quad\text{no scientific promotion}.\n\]\n\nThe mutable resident state is external to the release root:\n\n\[\nS_t\notin F_{sealed}.\n\]\n\nTherefore learning may change $S_t$ without changing the cryptographically sealed scientific program/data tree. This separation is part of the mathematical reproducibility model, not an implementation convenience.\n
# XXXII. AI acceptance composition — 15.10.2

The cognitive release uses two different mathematical predicates. Owner acceptance is

```math
A_i = \bigwedge_{g\in G_i} g = \mathrm{PASS},
```

where each owner $i$ evaluates its own complete gate set $G_i$ exactly once in the release acceptance run. Joint integration is a different predicate

```math
J = L \land B_{QPDTR} \land B_{cross} \land C_{live} \land R_{live} \land \bigwedge_i S_i,
```

where $L$ is current LawSpace qualification, $B$ are executable bridge/cross-domain bindings, $C_{live}$ and $R_{live}$ are the live Cognitive Core and Resident paths, and $S_i$ asserts that the separately accepted owner qualification surface remains present and callable. Thus $J$ does not redefine $A_i$ and does not execute $A_i$ a second time. This prevents qualification order or duplicated mutable-state replay from becoming part of the scientific/cognitive result.

The mutable resident state $M_t$ is external to the sealed scientific tree $S$:

```math
S_{t+1}=S_t\quad\text{during resident learning},
\qquad M_{t+1}=U(M_t,e_t),
```

with scientific promotion remaining subject to the ordinary owner/evidence/falsification gates. The controlled wake therefore demonstrates persistent cognitive-state evolution, not consciousness, AGI, or autonomous scientific truth assignment.

# XXXIII. Final 15.10.2 replay identity

Two independent current-test replays over the unchanged test-relevant layer (`source/`, `evaluation/`, `tests/`, `data/runtime/`) produced **59/59 + 59/59 PASS**, with zero historical nodes. Frozen plan digest: `380d6ad32daa8433f8575b3766363d1565a15c9d304a755acee08012e5d046bb`. Canonical aggregate replay digest: `858d26f1590418f59e3303ea59c15e902f51972e387aa0f1f9132cd5f59980e5`. All 30 batch receipts match across both runs. The only post-replay changes before sealing are documentation and `interfaces/joint_qualification.py`; tests reference neither joint implementation nor document contents (apart from asserting that the single canonical `MATHEMATICAL_BOOK.md` exists). A byte audit found 0 differences across 117 test-relevant files relative to the second completed replay tree.


# XXXIV. Adaptive multidimensional scientific subspace navigation — 15.11.0

## XXXIV.1 Scientific hypothesis space

Let the current canonical scientific-axis registry be

\[
\mathcal A_t=\{a_1,\ldots,a_{M_t}\},\qquad M_t=655.
\]

Atlas does not identify a scientific problem with the single full coordinate product over all 655 axes. Its structural hypothesis space is the union of **local subspaces**

\[
\boxed{\mathcal H(\mathcal A_t)=\bigcup_{k\ge 2}\{H_S:S\subseteq\mathcal A_t,\ |S|=k\}.}
\]

For the finite current registry the power set is finite, but its cardinality makes brute-force enumeration scientifically and computationally inappropriate. More importantly, a fixed maximum order would be an architectural claim that interactions above that order cannot matter. Therefore

\[
k_{\max}^{\mathrm{scientific}}=\mathrm{None}.
\]

The largest order materialized in one execution is an execution-state statistic, not an admissibility boundary.

## XXXIV.2 Why Atlas does not use a greedy pair-only expansion

A purely higher-order law can have vanishing or weak projections in every lower-order marginal. Hence a rule of the form

\[
S_{k+1}=\operatorname*{argmax}_{a\notin S_k}Q(S_k\cup\{a\})
\]

started only from pairwise empirical scores is structurally incomplete. 15.11.0 therefore separates **nomination** from later evidence ranking. Candidate local subspaces are nominated by the union

\[
\mathcal N=\mathcal N_{pair}\cup\mathcal N_{owner}\cup\mathcal N_{bridge}\cup
\mathcal N_{owner\text{-}merge}\cup\mathcal N_{semantic/role}.
\]

The current nomination modes are `EXACT_PAIR_FRONTIER`, `OWNER_COBOUND_HIGHER_ORDER`, `TYPED_BRIDGE_MOTIF`, `BRIDGE_CONNECTED_OWNER_MERGE`, and `SEMANTIC_ROLE_HIGHER_ORDER_MOTIF`. The last four can nominate a higher-order region without requiring a successful pairwise empirical projection.

## XXXIV.3 Local adaptive navigation

For a nominated subspace

\[
S=\{a_{i_1},\ldots,a_{i_k}\},
\]

Atlas derives a typed structural feature state

\[
z(S)=(D(S),R(S),C(S),O(S),B(S),G(S)),
\]

where `D` are domains, `R` axis roles, `C` coarse structural concepts, `O` authoritative owner bindings, `B` typed bridge coverage and `G` representation/attestation gaps.

Navigation is not a requirement to monotonically increase `k`. The admissible research actions are conceptually

\[
\mathcal U=\{\mathrm{EXPAND},\mathrm{SPLIT},\mathrm{MERGE},\mathrm{TEST},\mathrm{HOLD},\mathrm{REJECT\_ARTIFACT}\}.
\]

The current materializer implements independent local expansion lanes (`NEW_DOMAIN`, `NEW_ROLE`, `NEW_CONCEPT`, `SHARED_OWNER_GEOMETRY`, `TYPED_BRIDGE_EXTENSION`, `SEMANTIC_RESONANCE`, `BRIDGE_GAP_REDUCTION`) and preserves each alternative local branch instead of collapsing them into one giant owner-connected region. A later research cycle may re-enter any materialized candidate after new evidence, axis birth or representation birth.

There is no fixed neighbor-visit scientific budget. Runtime batching may limit one execution surface for isolation, but it cannot convert an unvisited subspace into a rejected scientific hypothesis.

## XXXIV.4 Candidate scientific contract

Each adaptive candidate has the state

\[
C(S)=\big(S,N,P,A,H,E,\Pi\big),
\]

where `N` is nomination provenance, `P` is the problem/question contract, `A` is applicability, `H` is a set of competing hypothesis/mechanism families, `E` is a discriminating-experiment blueprint and `Π` is the epistemic/prior-art state.

Potential problem classes include representation/observer gaps, cross-domain typed-bridge gaps, role disentanglement, non-Markovian memory, scaling/regime laws, stability boundaries, identifiability/reproducibility and thermal cross-domain response. A research-priority score may route computation, but

\[
Q_{priority}(S)\not\equiv P(\text{law true}\mid data),
\]

and it is never scientific evidence.

Before promotion the experiment contract requires, where applicable, lower-order projection controls, unit/convention controls, whole-adaptive-pipeline permutation/null calibration, non-overlapping regime holdout and independent world attestation. Thus

\[
E_{independent}=\varnothing\Longrightarrow\text{no scientific promotion}.
\]

## XXXIV.5 Literature and novelty

Prior-art search is post-freeze metadata, not a pre-freeze generator. For a candidate `c`,

\[
\boxed{\mathrm{NOT\_FOUND\_IN\_LITERATURE}(c)\not\Rightarrow\mathrm{FALSE}(c)}.
\]

Likewise, a known overlap does not delete a candidate: a known law in a new representation/domain may still answer a different scientific question. Possible post-freeze labels include `KNOWN_OVERLAP`, `PARTIAL_OVERLAP`, `KNOWN_MECHANISM_NEW_DOMAIN`, `KNOWN_LAW_NEW_REPRESENTATION`, and `NOVELTY_UNRESOLVED`.

## XXXIV.6 Current 15.11.0 execution state

The final pre-seal current scan over 655 axes scanned all 183,996 registered cross-domain pairs and materialized 256 exact pair-frontier candidates. Independent higher-order nomination plus local navigation produced 1,005 adaptive subspace candidates from 378 structural seeds. Their currently materialized axis orders span

\[
3\le k\le37,
\]

with both low-order and order-above-15 candidates present. This interval is not a configured bound.

The complete active ledger is

\[
|F|=256+1005+116+11+5+1=1394.
\]

All 1,394 entries remain candidate-level unless their own promotion protocol says otherwise. The 1,005 adaptive candidates replace the old six giant owner-connected region records as the authoritative higher-order materialization; the owner hypergraph itself remains the reachability substrate.


## XXXIV.7 Post-freeze novelty/prior-art operator

The discovery operator and the literature operator are deliberately ordered:

\[
S_k \xrightarrow{\mathcal N,\mathcal E} c_f
\xrightarrow{\mathrm{freeze}} d_f
\xrightarrow{\mathcal P_{lit}}
\{\mathrm{OVERLAP},\mathrm{PARTIAL},\mathrm{NOVELTY\!\_UNRESOLVED}\}.
\]

`\mathcal P_{lit}` has no edge back into the pre-freeze nomination graph. Thus prior knowledge can classify or save an experiment, but cannot manufacture the candidate that is later claimed as blindly discovered. For current 15.11.0 the frozen ledger contains 1,394 candidates and has SHA-256 `5bc30ce9a7291f49cebf78021b538c1e558e1ce97f629f6d63310f6eaa20541f`. Six selected local subspaces were reviewed post-freeze: three have direct known overlap, two have partial overlap, and one has related prior art without an exact typed match.

The epistemic rule is

\[
\mathrm{absence\ from\ searched\ literature}
\not\Rightarrow
\mathrm{falsehood},
\qquad
\mathrm{absence\ from\ searched\ literature}
\not\Rightarrow
\mathrm{novel\ law}.
\]

A novelty-unresolved candidate is therefore preserved until a scientific test, not discarded because search engines return no exact formula. Conversely, a known-overlap candidate remains useful as a calibration, transfer or new-domain representation candidate and is not silently deleted from the active frontier.

## Final 15.11.0 replay identity

Two independent fresh-copy transactional replays of the finalized 15.11.0 test-relevant tree produced **59/59 + 59/59 PASS** with zero historical nodes. Both runs used the identical frozen plan digest `f096668c03aecce69d9d657570fbcad1f4b99987b3c67697bc6f6f81b480a892` and produced the identical canonical aggregate digest `348ff3047d4b5dae04432ee05f989d82c0bbb7ecf3979abe4f958add238978ba`. All **30/30 batch receipt digests match A ↔ B**; volatile pytest timing/output is excluded from canonical result identity. No test was removed or weakened to obtain PASS, and runtime isolation limits are not scientific search ceilings.

\n\n# XXXV. Core Convergence: exact dimensional authority and adaptive Atlas — 15.12.0\n\n## XXXV.1 Why convergence is required\n\nThe first Atlas formulation and the current multidimensional explorer solve complementary parts of one problem. The current explorer nominates sparse local scientific subspaces without requiring a successful lower-order projection. The early mathematical kernel supplied exact dimensional reduction and explicit scientific qualification gates. 15.12.0 joins those two paths replacement-in-place rather than introducing another solver.\n\nThe scientific coordinate space remains\n\n\[\n\mathcal H = \bigcup_{k\ge 1}\{\mathcal H_S: S\subseteq\mathcal A, |S|=k\},\n\]\n\nwith adaptive owner-connected navigation. Expression trees are not promoted to the primary search space.\n\n## XXXV.2 Canonical seven-dimensional metrology authority\n\nAll law-space dimensions are represented internally in the canonical SI basis\n\n\[\n\mathbf d(q)=(d_L,d_M,d_T,d_I,d_\Theta,d_N,d_J)\in\mathbb Z^7.\n\]\n\nFor a selected quantity set \(S=\{q_1,\ldots,q_n\}\), Atlas builds\n\n\[\nD_S=[\mathbf d(q_1)\;\cdots\;\mathbf d(q_n)]\in\mathbb Z^{7\times n}\n\]\n\nand computes the right nullspace exactly over \(\mathbb Q\):\n\n\[\n\ker_{\mathbb Q}D_S=\{a\in\mathbb Q^n:D_Sa=0\}.\n\]\n\nThe implementation authority is the already-existing rational RREF/nullspace code in `source/phi_compiler_owner.py`; `source/lawspace/scientific_axis_space.py` projects typed quantity descriptors into that authority and exposes the result as a qualification receipt. No second rational algebra implementation is created.\n\nThe exact rank and nullity are\n\n\[\nr=\operatorname{rank}_{\mathbb Q}D_S,\qquad p=n-r.\n\]\n\nEach null vector defines a dimensionless Buckingham group \(\pi=\prod_i q_i^{a_i}\). The basis is not itself unique; Atlas records the computed rational basis as a reproducible coordinate certificate, not as a claim that this basis is the only physical parameterization.\n\n## XXXV.3 Legacy five-coordinate descriptors\n\nHistorical scientific-axis tests supplied reduced five-coordinate descriptors. 15.12.0 retains them only at the compatibility boundary. They are padded to seven components before any search or kernel operation and are marked in the returned receipt by `legacy_dimension_padding_used=true`. New domain adapters are required to use the seven-coordinate authority. The compatibility path is not evidence that five dimensions are a valid universal physical basis.\n\n## XXXV.4 Qualification sequence after nomination\n\nAdaptive subspace nomination and scientific qualification are distinct stages. A raw born coordinate or an exactly fitted relation is not automatically a law. The common contract is now explicit:\n\n1. exact 7D dimensional kernel;\n2. exponent/coordinate description complexity;\n3. convention-artifact audit when an alternate metrology convention is declared;\n4. known-law/source derivability audit;\n5. data-collapse/invariance evidence where multi-system observations exist;\n6. regime-transition/OOD checks;\n7. cross-system transfer/replication;\n8. whole-pipeline permutation null before scientific promotion;\n9. competing mechanisms and discriminating experiment when identifiability remains unresolved.\n\nThe expensive gates are not executed on every raw subspace. Nomination remains broad; promotion remains fail-closed.\n\n## XXXV.5 Invariant preserved from 15.11.0\n\nHigher-order nomination does not require a successful pairwise or lower-order projection. Therefore the convergence does not reintroduce the greedy-blindness defect. Exact dimensional structure is a nomination/qualification principle, not a requirement to grow every candidate from order one or two.\n\n## XXXV.6 Claim boundary\n\n15.12.0 establishes a software and mathematical integration result: the current Atlas law-space path has one canonical 7D dimensional representation and one reused exact rational nullspace authority. It does not establish a new natural law. Whole-pipeline permutation calibration, OOD/regime evidence and independent replication remain required before any promoted discovery claim.\n

## XXXV.7 Verification identity

The finalized 15.12.0 convergence path passed the existing transactional current-only replay with **61/61** test nodes. Plan digest: `d161ffe77923c050d6299ab1737f3119c224d6501ce0530e703423ce7d84961d`; canonical aggregate digest: `27b4ad0e28fd54f6ebfc2c447bcdf739342f9fbbb9e1c12fc8c62c25f6433d88`. Current-state qualification passed **44/44** and joint owner qualification returned `PASS_JOINT_CURRENT_15_12_0`. These receipts qualify the software state; they do not promote a scientific discovery.


# XXXVI. Qualification Runtime Convergence — 15.13.0

## XXXVI.1 Purpose and authority

15.13.0 does not introduce a second promotion engine. The sole authoritative scientific promotion owner remains the existing `ScientificPromotionCore`, upgraded replacement-in-place to `SCIENTIFIC-PROMOTION-CORE/9.0.0`. The purpose of this release is to make the qualification sequence established in XXXV executable for every persistent frontier candidate rather than leaving it as a partly declarative contract.

Let a persistent Atlas candidate record be

\[
c=(\mathrm{id},\mathrm{class},\mathrm{payload},\mathrm{owners},\mathrm{status},\ldots).
\]

The runtime computes one ordered gate vector

\[
U(c)=(u_0,u_1,\ldots,u_{10}),
\]

with the invariant order

\[
\begin{aligned}
u_0&=\text{record integrity},\\
u_1&=\text{typed hypothesis binding},\\
u_2&=\text{exact dimensional qualification},\\
u_3&=\text{convention-artifact audit},\\
u_4&=\text{known/source derivability audit},\\
u_5&=\text{collapse or invariance evidence},\\
u_6&=\text{distinct-regime/OOD evidence},\\
u_7&=\text{cross-system replication},\\
u_8&=\text{whole-pipeline permutation null},\\
u_9&=\text{discriminating experiment},\\
u_{10}&=\text{numeric scientific-promotion readiness}.
\end{aligned}
\]

Every materialized record uses the same ordered path. Candidate class changes the evidence available and the legitimate terminal branch; it does not create a different hidden promotion standard.

## XXXVI.2 Fail-closed epistemic semantics

A missing gate is not interpreted as negative evidence. For each evidence-bearing gate Atlas distinguishes at least

\[
\{\mathrm{PASS},\;\mathrm{PENDING\_EVIDENCE},\;\mathrm{KNOWN\_DERIVED\_ROUTE},\;\mathrm{AXIS\_ROUTE}\}.
\]

In particular,

\[
\mathrm{missing\ evidence}\;\not\Rightarrow\;\mathrm{candidate\ false}.
\]

A generic unresolved candidate therefore remains

\[
\mathrm{FRONTIER\_QUALIFICATION\_PENDING\_EVIDENCE},
\]

not `FALSE`. This restores the intended Atlas distinction between an unexplored frontier and a falsified scientific hypothesis.

Source-derived algebraic consequences and operator compositions are a separate epistemic branch. If a formal candidate is already derivable from accepted source laws, Atlas records that fact and retains the object for routing/reuse, but does not promote it as an independent new law:

\[
\mathrm{KNOWN\_SOURCE\_DERIVED\_CONSEQUENCE}
\Rightarrow
\neg\mathrm{INDEPENDENT\_NEW\_LAW\_PROMOTION}.
\]

Likewise a provisional measurable coordinate is routed to the pre-existing Dynamic Axis Promotion owner; law promotion is not used as a shortcut for axis birth.

## XXXVI.3 Whole-pipeline permutation null

The null gate calibrates the adaptive *procedure*, not only the final fitted formula. Let \(\mathcal P\) denote the complete proposer/selector/qualifier path whose best score on observed data is \(m_*\). For permutation \(b\), the target/evidence association is broken according to the declared null and the same complete pipeline is rerun, producing best null score \(m_b\).

For a lower-is-better metric the empirical one-sided p-value is

\[
\hat p=\frac{1+\sum_{b=1}^{B}\mathbf 1[m_b\le m_*]}{B+1}.
\]

For a higher-is-better metric the inequality is reversed. The current runtime contract requires

\[
B\ge 200,\qquad \hat p\le 10^{-2},
\]

with a trusted evidence owner, explicit method identifier, evidence digest and pipeline digest. These numerical defaults are release-policy thresholds, not universal constants of nature.

The critical semantic condition is

\[
\boxed{u_8=\mathrm{PASS}\text{ only for a null distribution of the whole declared adaptive pipeline}.}
\]

A null distribution for one post-selected regression fit is insufficient to satisfy this gate.

## XXXVI.4 Digest-bound frontier promotion receipt

The executable path is serialized as `phi-frontier-promotion-path/v1`. Define the candidate core as the record before the outer ledger digest and before the newly attached promotion receipt:

\[
h_c=\mathrm{SHA256}(\mathrm{canonical}(c_{\rm core})).
\]

The receipt \(R_c\) contains the candidate identifier/class, \(h_c\), owner/version, the complete gate sequence, individual gate outcomes, next unresolved gate, terminal status and claim boundary. Its receipt identity is content-addressed:

\[
h_R=\mathrm{SHA256}(\mathrm{canonical}(R_c\setminus\{\mathrm{OUTPUT\_HASH},\mathrm{RECEIPT\_ID}\})).
\]

The ledger record then receives its outer `record_digest` after the receipt is attached. This two-layer construction binds scientific qualification to candidate semantics and then binds both candidate and receipt into the persistent ledger row.

A receipt is invalid if its hash is wrong, its schema/owner is wrong, its gate sequence is incomplete/reordered, or its candidate identity does not agree with the request that later seeks promotion.

## XXXVI.5 Non-bypassable numeric promotion

The earlier numeric `evaluate()` path remains authoritative for uncertainty, fit, alternatives, identifiability, OOD and replication. 15.13.0 adds a gate in front of the final law transition rather than replacing those checks.

Let \(G_{-2}\) mean that a valid frontier receipt is supplied, `prepromotion_ready=true`, the receipt is included in the content-addressed scientific-verification artifact set, and its candidate ID agrees with the numeric request. Let \(G_{-1},G_0,\ldots,G_7\) denote the existing formal/numeric/world gates. Then

\[
\boxed{\mathrm{LAW\_CANDIDATE}\Rightarrow G_{-2}\land\bigwedge_{i=-1}^{7}G_i.}
\]

Conversely, satisfying the old numeric/world gates while omitting \(G_{-2}\) cannot produce `LAW_CANDIDATE`; the result is bounded above by the prior non-final scientific state (for the fully replicated case, `REPLICATED`). Thus a caller cannot bypass convention/derivability/null/experiment qualification by invoking the old numeric API directly.

## XXXVI.6 Runtime result on the current frontier

The finalized 15.13.0 frontier scan materializes the same **1,394** candidate IDs and attaches a valid unified path receipt to **1,394/1,394** records. The actual gate state is intentionally conservative:

- `U0_RECORD_INTEGRITY`: 1,394 pass;
- `U1_TYPED_HYPOTHESIS_BINDING`: 328 pass;
- `U2...U10`: no current persistent candidate has the complete trusted evidence packet required by the unified runtime;
- prepromotion-ready: 0;
- promotion allowed: 0;
- candidate marked false due to missing evidence: 0;
- source-derived/operator branch retained-not-new-law: 127;
- provisional-axis branch routed to axis promotion: 1;
- ordinary/pending qualification branch: 1,266.

The next unresolved gate is `U1` for 1,066 records and `U2` for 328 records. This is not “nothing found”; it is a machine-readable map of exactly which evidence layer is missing for each active research object.

Current ledger SHA-256 after the finalized source-contract pass:

`c65ba873718ab020e56672973b0f5295ff42f9a457d40c61eadb9cd618813d0e`.

Current frontier report digest:

`7e902d01e11b37d5d1741deb78e5af2417bf2ffacb7a408936a87f722ee8bfd7`.

## XXXVI.7 Prior-art preservation during receipt migration

Adding a receipt changes the persistent ledger bytes and therefore invalidates a prior-art artifact that was cryptographically bound to the previous ledger hash. The six literature assessments were not rerun or reclassified merely to repair that binding.

The migration audit found the same 1,394 candidate IDs. Relative to the immediately preceding 15.13 scan, 1,393 candidate scientific cores were byte-identical; the one provisional-axis record changed only through the nested low-frequency-analysis digest cascade. After excluding that nested digest pointer, its scientific payload/experiment semantics were unchanged. The prior-art artifact is therefore rebound with explicit migration provenance while preserving all six reviews and classifications.

This is a cryptographic migration statement, not new literature evidence.

## XXXVI.8 Claim boundary and next open frontier

15.13.0 establishes an executable software qualification invariant. It does not establish that any of the 1,394 frontier records is a law of nature. A valid `FPR` states where a candidate is in the qualification process and what is missing; it is not itself world evidence.

The next architectural frontier after this release is fair open-ended traversal: finite local computational budgets must become resumable/dovetailed search shells rather than hidden terminal boundaries. That traversal work is deliberately not conflated with the present promotion-path convergence.

# XXXVII. FAIR OPEN-ENDED TRAVERSAL / DOVETAIL CONVERGENCE — 15.14.0

## XXXVII.1 Why open-ended policy is not enough

A search implementation can declare `fixed_order_ceiling = null` and still starve a finite scientific region if every execution repeatedly spends its finite budget on newly attractive neighbors. 15.14.0 therefore distinguishes

\[
	ext{no declared global ceiling}
\quad	ext{from}\quad
	ext{fair eventual addressability}.
\]

The 15.13 materialized frontier is not regenerated by a new algorithm. It is the immutable initial node set of the continuation scheduler. The active ledger remains byte-identical with 1,394 records and 1,005 adaptive nodes.

## XXXVII.2 Append-only axis birth rank and diagonal pair schedule

Let the ever-registered canonical/research axis stream have append-only birth order

\[
A^{\infty}=(a_0,a_1,a_2,\ldots),\qquad b(a_i)=i.
\]

Existing birth ranks never change. Newly registered axes are appended. Pair seeds are scheduled by the diagonal family

\[
P_j=\{(a_i,a_j):0\le i<j\},\qquad j=1,2,3,\ldots.
\]

Thus a finite-rank pair `(a_i,a_j)` is visited after a finite number of pair visits. Continuous append-only axis birth cannot move that pair to a later diagonal because its birth ranks are immutable. This is stronger than a lexicographic cursor over a growing registry.

## XXXVII.3 Finite-round node fairness

Let `N(t)` be the finite set of materialized content-addressed nodes at the start of a node round. A round freezes

\[
R_r=\operatorname{snapshot}(N(t_r))
\]

and visits every member of `R_r` exactly once before constructing the next snapshot. Nodes born while `R_r` is executing do not enlarge the current round; they enter `R_{r+1}`. Consequently every node that exists at a finite time receives another visit after finitely many scheduler steps.

Each node stores an axis cursor. On a node visit it considers the next append-only axis address and materializes the union if the axis is missing. Because a node receives infinitely many visits under unbounded repeated advancement, every finite birth-rank axis is eventually considered for that node. Inductively, every finite subset of ever-registered axes has a finite construction path. The guarantee is conditional on repeated advancement; a finite tranche is never called exhaustive.

## XXXVII.4 Dovetailed local scientific search shells

For each materialized subspace `S`, local model exploration has shell index

\[
s(S)=0,1,2,\ldots.
\]

Shell zero preserves the complete 15.13 execution envelope. For positive shells, local budgets expand monotonically. In the current implementation, representative budgets have the form

\[
B_s=B_0(s+1),\qquad O_s=O_0+s,
\]

with support clipped only by the finite number of axes actually present in that local dataset. Therefore prior values such as support order, exponent order, feature caps and sparse-term counts are **per-shell execution budgets**, not scientific-space boundaries. `fixed_maximum_shell = null`.

This does not imply that every shell is computationally cheap, nor that an infinite computation finishes. It establishes resumability and absence of a hidden finite terminal shell.

## XXXVII.5 Persistent state and sealed/mutable separation

The scheduler state is serialized as `phi-fair-open-ended-dovetail-state/v1` and content-addressed by a canonical digest. It contains at least

- append-only `axis_birth_order`;
- content-addressed node map;
- diagonal pair cursor;
- finite-round node snapshot/cursor;
- per-node axis cursor and local search shell;
- environment epoch/rebase provenance;
- last-advance receipt and fairness contract.

The sealed release contains only the initial current snapshot at `data/frontiers/ATLAS_DOVETAIL_STATE_CURRENT.json`. Mutable advancement resolves through external runtime state. Let `S_0` be the sealed snapshot and `T_n` a finite advance operation. Then

\[
S_{n+1}=T_n(S_n),\qquad\mathrm{storage}(S_{n+1})
ot\subset\mathrm{sealed\ release\ root}.
\]

No advance is allowed to delete old nodes. Environment changes append new axes and preserve old progress; requalification may change evidence status but does not erase the historical address.

## XXXVII.6 Preservation theorem for the 15.13 frontier

The release acceptance uses the 15.13 ledger as a byte-level control, not merely a cardinality control. After 15.14 materialization,

\[
\mathrm{SHA256}(L_{15.14,\,sealed})
=\mathrm{SHA256}(L_{15.13})
=	exttt{c65ba873718ab020e56672973b0f5295ff42f9a457d40c61eadb9cd618813d0e}.
\]

All 1,394 records, including all 1,005 adaptive multidimensional records, are preserved. The dovetail state is a separate continuation address map; it is not a replacement ledger.

## XXXVII.7 Fairness claim boundary

15.14.0 establishes a software scheduling property, not completeness of science. The valid implication is

\[
	ext{finite birth-rank subset}+	ext{unbounded repeated fair advancement}
\Rightarrow	ext{eventual address/materialization}.
\]

The following implications are forbidden:

\[
	ext{not yet visited}\Rightarrow	ext{false},
\qquad
	ext{finite tranche completed}\Rightarrow	ext{space exhausted},
\qquad
	ext{materialized}\Rightarrow	ext{law}.
\]

Scientific promotion remains governed by the 15.13 `U0...U10` qualification runtime. The dovetail scheduler decides **where/when to continue investigation**; it does not decide scientific truth.



# XXXVIII. KNOWLEDGE-BINDING / HYPOTHESIS MATERIALIZATION — 15.15.0

## 38.1 From open-ended discovery to typed depth

15.14.0 established fair persistent traversal, but fair traversal can discover scientific regions faster than the ontology can type them. For a frontier subspace

\[
S=\{a_1,\ldots,a_k\},
\]

let \(B(a)\) be the canonical owners that explicitly bind axis \(a\). A region is typed only when all its coordinates have owner support and all required cross-domain pairs have declared bridges:

\[
\operatorname{Typed}(S)\iff
(\forall a\in S:|B(a)|>0)\land
(\forall(d_i,d_j)\subseteq D(S):\operatorname{Bridge}(d_i,d_j)).
\]

Therefore

\[
B(a)=\varnothing\Rightarrow \mathrm{PENDING\_TYPED\_AXIS\_OR\_BRIDGE\_BINDING},
\]

not `FALSE`.

## 38.2 Qualified owner-axis binding overlay

15.15.0 keeps the existing `LawCatalog` as the only passport/owner authority. A qualified ontology overlay

\[
\mathcal B\subseteq\mathcal O\times\mathcal A
\]

is loaded from the existing `knowledge_evolution_state.json`. A production binding \((o,a)\) is accepted only when the owner and axis already exist, belong to the same domain unless a separate typed bridge exists, the exact current owner digest is bound, and at least one internal semantic witness is present in the owner's scientific coordinate, formula, assumption or observable.

The binding is routing/typing evidence only:

\[
\operatorname{OwnerAxisBinding}\not\Rightarrow\{\text{new law, world evidence, novelty, bridge}\}.
\]

The canonical 15.15 state contains three qualified receipts covering two axes:

- `aeronautics_and_aerostation.actuator_bandwidth` ← `AERO-AEROSERVOELASTIC-STATE-SPACE`;
- `aeronautics_and_aerostation.actuator_bandwidth` ← `AERO-STATE-FEEDBACK-CONTROL`;
- `chemistry.photochemical_regime` ← `OCH-035`.

Gaps without sufficient current-owner evidence — including `directional_stability`, `aeroelastic_divergence` and `physics.detector_coupling` — remain explicitly unbound/PENDING.

## 38.3 Preservation and progressed sealed state

The progressed external 15.14 dovetail state is promoted into the 15.15 sealed snapshot instead of being discarded. Current adaptive state:

\[
|N|=3204,
\]

with 1,005 preserved 15.13 baseline nodes, 2,175 explicit fair-dovetail continuation nodes, and 24 additional requalification-born nodes exposed by the changed binding environment. The active candidate ledger is

\[
|L_{15.15}|=3593.
\]

An external comparison against sealed 15.14 verifies

\[
\boxed{L_{15.14}^{ID}\subseteq L_{15.15}^{ID}},\quad |L_{15.14}^{ID}|=1394,\quad |L_{15.14}^{ID}\setminus L_{15.15}^{ID}|=0.
\]

The preservation claim is identity preservation, not byte identity: 65 legacy records legitimately receive enriched core payloads after ontology requalification, while their candidate identities remain intact.

## 38.4 Relational hypothesis materialization

A fully typed subspace is still not a law. The existing `ScientificPromotionCore` is upgraded replacement-in-place to `SCIENTIFIC-PROMOTION-CORE/9.1.0` and gains a structural materialization operation

\[
H_S=(S,O_S,H_0,\{H_j\},E_S),
\]

where \(S\) is the frozen axis set, \(O_S\) is frozen owner support, \(H_0\) is an owner-factorized/direct-sum null family, \(\{H_j\}\) are competing interaction families, and \(E_S\) is the discriminating measurement contract.

No scalar relation or coefficient is invented:

\[
\operatorname{scalar\_equation\_frozen}(H_S)=\mathrm{False}.
\]

Hence U2 and U3 may pass only as explicit non-applicability for a non-scalar relational representation:

\[
U2=\mathrm{PASS}_{N/A},\qquad U3=\mathrm{PASS}_{N/A},
\]

while U4 remains mandatory:

\[
U4=\mathrm{PENDING\_KNOWN\_DERIVABILITY\_AUDIT}.
\]

No materialization may skip U4 or empirical gates U5–U10.

## 38.5 Depth result

From the frozen 2,175 new dovetail IDs, **254** are fully typed in the current owner/bridge environment and are persisted as digest-bound relational hypotheses. Current unified gate census:

| gate | passing records |
|---|---:|
| U0 record integrity | 3,593 |
| U1 typed binding | 604 |
| U2 exact-dimensional / relational N/A | 254 |
| U3 convention / relational N/A | 254 |
| U4 known derivability | 0 |
| U5 collapse/invariance | 0 |
| U6 distinct-regime OOD | 0 |
| U7 cross-system replication | 0 |
| U8 whole-pipeline null | 0 |
| U9 observed discriminating experiment | 0 |
| U10 numeric promotion | 0 |

Thus

\[
\boxed{254:\mathrm{typed}\rightarrow\mathrm{materialized}\rightarrow U3},\qquad
\boxed{0:\mathrm{automatic\ law\ promotions}}.
\]

Materialization increases scientific depth, not epistemic rank.

## 38.6 Architecture and remaining work

The current chain is

\[
\text{Fair Dovetail Search}\to\text{Qualified Binding}\to\text{Relational Materialization}\to U0\ldots U10\to\text{World Evidence}.
\]

Search nominates; Knowledge Evolution types; ScientificPromotionCore materializes/adjudicates; only measured, uncertainty-aware and independently qualified evidence may pass empirical gates. The next depth frontier is U4 derivability for the 254 materialized hypotheses, followed only for survivors by U5–U10. Fair dovetail remains active as a memory/coverage mechanism, not as a requirement to repeatedly rescore the old 1,394 records.


# 39. P2 Closure and Scientific Audit Depth — CURRENT 15.16.0

## 39.1 Conservation laws: equivalence class before canonical representative

Trajectory constancy alone does not identify a unique physical observable. If an invariant \(I\) is constant along every trajectory, then for any injective monotone map on the observed range,

\[
I\sim f(I),
\]

and multiplication by a trajectory-constant factor also preserves constancy. Therefore neither the within-trajectory eigensolver nor a collapse criterion may by itself distinguish energy from specific energy, its square, logarithm, or a constant rescaling. The invariant finder identifies an **equivalence class**, not a canonical physical representative.

The canonicalization contract is therefore fail-closed:

\[
\boxed{\text{constancy evidence}\not\Rightarrow\text{canonical physical observable}}.
\]

A canonical representative may be selected only after an independent composition/extensivity principle is declared. For the mechanical-energy control, the invariant finder can return the specific invariant

\[
e=gh+\frac12v^2.
\]

If mass \(m\) is independently declared a trajectory-constant extensive carrier and energy is required to be additive under composition of independent massive subsystems, the canonicalization map is

\[
\mathcal C_m[e]=m e=mgh+\frac12mv^2.
\]

Normalization is then fixed by the declared anchor coefficient, not by numerical eigenvector scale. Without the composition law, the runtime returns `CANONICALIZATION_BLOCKED_COMPOSITION_LAW_REQUIRED`. This closes the original \(E\) versus \(E/m\) reproducibility defect without pretending that constancy itself contains the missing thermodynamic/compositional semantics.

## 39.2 Resident AI state: digest-bound restore and migration

Resident state is operational memory, not scientific truth. Let \(B\) be the raw snapshot bytes and \(S\) the decoded state. Restore requires two independent checks:

\[
H(B)=h_{expected},\qquad H_{state}(S)=S[\texttt{state_digest}].
\]

Only after both pass may schema migration occur. A supported migration is a pure map

\[
M_{q\to5}:S_q\mapsto S_5
\]

that changes representation/schema fields and, when necessary, rebinds the runtime `SYSTEM_RELEASE`; it does not change evidence, candidate epistemic status, accepted laws, or scientific claims. The target is written atomically to an **external** state directory and an existing target is not overwritten without an explicit flag.

The executable interface is:

```text
python interfaces/phi_compiler_cli.py resident-state-restore \
  --snapshot <snapshot.json> \
  --expected-sha256 <sha256> \
  --state-dir <external-dir>
```

The receipt binds source hash, source/target schema, source/target system release, migration steps, target state digest, destination, and the invariant `scientific_truth_changed=false`.

## 39.3 Four independent version coordinates

The old ambiguous scalar `RELEASE` is replaced by a version vector

\[
\boxed{V=(V_{sys},V_{component},V_{state},V_{AI})}.
\]

For 15.16.0:

\[
V=(15.16.0,\ 6.0.0,\ 5,\ 15.10.2).
\]

The coordinates have different semantics:

- `SYSTEM_RELEASE` identifies the sealed integrated system;
- `COMPONENT_SCHEMA_VERSION` identifies the resident-cognitive component contract;
- `STATE_SCHEMA_VERSION` identifies serialized resident-state structure;
- `AI_ACCEPTANCE_VERSION` identifies the external AI-owner acceptance snapshot against which compatibility is tracked.

No equality or ordering relation between these coordinates is implied. Updating one does not silently rewrite the others.

## 39.4 Strict read-only audit

A qualification path is read-only only if the complete sealed tree is observationally identical before and after execution. Define a tree snapshot

\[
T(R)=\{(p,\operatorname{type}(p),H(p),|p|,\operatorname{link}(p))\}_{p\in R}.
\]

The strict audit executes current-state qualification, joint scientific+AI qualification and closed-world seal under `PYTHONDONTWRITEBYTECODE=1` with resident state redirected to an external temporary directory. It then requires

\[
\boxed{T_{before}(R)=T_{after}(R)}
\]

including files, directory set and symlink targets. Created, removed or modified paths are a failure even when scientific checks pass. The executable gate is:

```text
make audit-read-only
```

The audit itself persists no receipt inside the sealed tree; otherwise the proof would be self-defeating.

## 39.5 U4: formal known-derivability audit of the 254 frozen hypotheses

The 254 materializations frozen in 15.15 remain the population under test. No post-hoc candidate selection is introduced. For a relational materialization \(H\), the formal U4 question is narrower than novelty:

\[
\text{Do the already accepted source-owner facts logically force the selected joint typed interaction?}
\]

`ScientificPromotionCore/9.2.0` validates the materialization digest, source-owner acceptance, the explicit joint-interaction alternative and the null family `OWNER_FACTORIZED_OR_DIRECT_SUM_NULL`. A U4 pass means only:

\[
\boxed{H\ \text{is not formally forced by merely accepting its source owners}.}
\]

It does **not** mean that nature realizes \(H\), that the interaction is novel in literature, or that a quantitative law has been established. All 254 frozen relational hypotheses obtain this formal U4 receipt.

## 39.6 U5–U10 remain evidence-gated

The next gate requires measured world evidence for collapse/invariance. The shipped materializations contain no admissible independent measurement set sufficient to execute U5. Therefore the correct state is

\[
U4=254,\qquad U5=U6=\cdots=U10=0.
\]

This is a completed audit, not an incomplete implementation: absence of world evidence is represented explicitly as `PENDING`, never as `FALSE` and never as an automatic promotion. The scientific chain remains

\[
\text{typed hypothesis}\to U4\to\boxed{\text{world measurement required}}\to U5\ldots U10.
\]

## 39.7 Closure of the original architectural reconstruction plan

With 15.16.0, the original P0/P1/P2 reconstruction sequence is closed at the architectural level:

\[
\text{exact 7D core}\to\text{unified qualification}\to\text{fair dovetail}\to\text{knowledge binding/materialization}\to\text{P2 closure}.
\]

Future work is scientific exploration and evidence acquisition, not repair of the four P2 debts closed here.


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


## 15.18.0. Evidence-scoped alpha model for open-ended Genesis

Let an evidence credit

\[
c_i=(e_i,D_i,S_i,a_i)
\]

consist of persistent evidence identity \(e_i\), scientific domain \(D_i\), measured-axis support \(S_i\), and remaining alpha credit \(a_i\ge 0\). A Genesis query is

\[
Q=(D_Q,A_Q),\qquad A_Q=\{y\}\cup X,
\]

where \(y\) is the target axis and \(X\) is the set of input axes. The query may consume \(c_i\) only when

\[
D_i\in\{D_Q,*\},\qquad A_Q\subseteq S_i\quad\text{or}\quad *\in S_i.
\]

### Persistent evidence identity

The coordinate \(e_i\) is an **evidence fingerprint**, not a caller-selected sample label. For an acquisition event with source owner \(O\), upstream evidence records \(E\), and measured semantic quantities \(M\), the production research loop computes

\[
\boxed{e_i=H_{\mathrm{acq}}(O,E,M)}.
\]

`sample_id` is deliberately excluded from this identity. Therefore aliases of the same acquisition cannot create new alpha. A scoped scientific grant without a stable evidence fingerprint fails closed. A reused `sample_id` bound to a different fingerprint is an identity conflict and is also refused.

The ledger cannot prove statistical independence from payload bytes alone. Stable evidence identity and independence remain obligations of the acquisition owner/source contract; the ledger preserves that identity, prevents reminting, and prevents double spending.

### Compatible balance and destructive debit

The compatible balance available to query \(Q\) is

\[
B(Q)=\sum_{i:\,c_i\models Q} a_i.
\]

A search priced at \(P\) is affordable iff

\[
B(Q)\ge P.
\]

Debit is globally destructive:

\[
a_i\leftarrow a_i-d_i,\qquad \sum_i d_i=P.
\]

Thus one evidence event cannot finance several independent search contexts by aliasing or by moving between domain/axis subspaces. There is no fixed balance cap:

\[
\boxed{\texttt{max\_balance\_bp}=\varnothing}.
\]

Reachable depth grows only through genuinely new compatible evidence.

### Open-ended shell pricing

For shell \(G_k\), let \(F_k\) be its finite canonical family prefix and let \(m\) be the permutation count. With per-family price \(p_F\) and per-permutation price \(p_\pi\), the search price is

\[
P_k=\bigl(|F_k|-|F_{k-1}^{\mathrm{paid}}|\bigr)p_F+m p_\pi.
\]

On a new split, \(|F_{k-1}^{\mathrm{paid}}|=0\), so the full search is paid. On the same split, a strict shell extension pays only the unpaid family increment. A same-or-smaller shell is a duplicate refusal and consumes zero alpha because no new experiment is executed.

Each \(G_k\) is finite and deterministic, while

\[
k\in\mathbb N
\]

has no terminal value. Open-endedness is therefore a limit of finite certified computations rather than an infinite single computation.

### Bounded pre-materialisation

The atomic-term generator produces only the canonical prefix required by the family budget. It walks degree layers in deterministic order and stops when the required atom prefix is complete; it does not first construct the entire deep grammar and truncate afterwards. This makes the family cap a real pre-materialisation resource boundary rather than a post-hoc slice.

### Epistemic separation

Statistical accounting and scientific truth remain separate. A family exposed to a sealed split can become split-local ineligible with an explicit reason such as `NULL_FAILED`, `SEALED_BELOW_MARGIN`, or `SEAL_EXPOSED_NULL_MISSING`. These states prevent illegal reuse of the same sealed question; none is automatically a statement that the corresponding law is globally false outside the tested validity domain.

The authoritative 15.18 version vector is

\[
(\text{system release},\text{component schema},\text{state schema},\text{AI acceptance})
=(15.18.0,6.0.0,5,15.10.3).
\]


## 15.19.0. Fresh-epoch autonomous Genesis and sequential exact permutation control

### 15.19.0.1 Decision/test separation

For target context `q=(D,Y,X)` let `A_k` denote the assessment epoch used only to decide whether another search is warranted. If the decision fixes shell `G_k`, the system then acquires a fresh confirmation epoch `C_k`. The admissibility invariant is

```math
A_k \cap C_k = \varnothing,\qquad C_i \cap C_j = \varnothing\;(i\ne j),
```

and only `C_k` may enter the Genesis FIT/SEAL split for that search. Therefore data used to select `G_k` are not reused to evaluate the search selected by that decision.

### 15.19.0.2 Exact finite-permutation gate

For observed whole-pipeline statistic `T_obs` and `N` permutation replays,

```math
p_N = \frac{1 + \sum_{i=1}^{N} \mathbf 1[T_i \ge T_{obs}]}{N+1}.
```

A finite permutation gate at level `alpha` is resolvable only if

```math
\frac{1}{N+1}\le \alpha.
```

If this fails, the epistemic result is `INSUFFICIENT_NULL_RESOLUTION`, not PASS and not FAIL. Otherwise PASS requires `p_N <= alpha`.

### 15.19.0.3 Sequential union-bound controller

The temporary per-target controller uses the exact rational schedule

```math
\alpha_k = \frac{\alpha_{tot}}{2^{k+1}},\qquad k=0,1,2,\ldots
```

so

```math
\sum_{k=0}^{\infty}\alpha_k = \alpha_{tot}.
```

The minimum exact permutation count is

```math
N_k = \left\lceil \frac{1}{\alpha_k} \right\rceil - 1.
```

For `alpha_tot=0.05` the first counts are `39,79,159,319,639,...`. This is a valid per-target sequential family-wise error allocation by union bound when each confirmation epoch is fresh and each attempt is judged at its preregistered `alpha_k`. It is **not** an anytime-valid e-process and makes no global many-target FDR guarantee.

### 15.19.0.4 Resource deferral is not epistemic rejection

A compute owner may refuse immediate execution when `N_k` or shell cost exceeds current resources. The resulting state is

```text
DEFERRED_RESOURCE
```

and preserves the shell, attempt index, exact rational level and required permutation count. It must not be mapped to FALSE, exhausted search space, or terminal shell.

### 15.19.0.5 Distinct accounting coordinates

The statistical level `alpha_k`, Genesis search price and promotion price are independent coordinates. In particular, tightening the statistical level must not make promotion cheaper. Evidence-scoped ledger credits remain bound to domain/axis support and persistent acquisition fingerprints from the 15.18 acquisition boundary.

### 15.19.0.6 Open mathematical frontier

The halving controller is retained only as a correct finite/sequential bridge. The planned next owner is a permutation e-process/e-value research owner satisfying conditional e-validity on fresh epochs, followed by an online multi-target discovery controller. Neither guarantee is claimed in 15.19.0.

## 15.19.1. Identity/evidence repair without scientific-behaviour promotion

This patch changes no accepted scientific decision rule from 15.19.0. Its purpose is to make the release identity and evidence statements injective and machine-readable. The authoritative version vector is

\[
(	ext{system}=15.19.1,\ 	ext{AI acceptance}=15.10.4,\ 	ext{component schema}=6.0.0,\ 	ext{state schema}=5,\ 	ext{scienceatlas-ai}=0.9.0).
\]

The current valid sequential controller has verified only the resource frontier on the blind fixture. Therefore

\[
	exttt{blind\_law\_capability\_verified\_under\_current\_valid\_controller}=\mathrm{false}.
\]

The earlier exact recovery of \(2-7/x+5xz\) is historical mechanism evidence only, not current acceptance evidence, because its null was later superseded: with \(N=8\), \(p_{\min}=1/9>0.05\), so the claimed level was arithmetically unattainable.
\n\n## 15.20.0 — finite-group permutation e-process layer\n\nFor a fresh epoch dataset \(D\), a finite permutation group \(S\) fixed before acquisition, and deterministic Genesis score \(g(D)\), the qualified exact score family is\n\n```math\nW_q(D)=(1+g(D))^q,\qquad q\in\{1,2,4,8\}.\n```\n\nEach component is normalized over the complete group,\n\n```math\ne_q(D)=\frac{W_q(D)}{|S|^{-1}\sum_{\pi\in S}W_q(D^\pi)},\n```\n\nand the preregistered mixture is\n\n```math\ne(D)=\frac14\sum_{q\in\{1,2,4,8\}}e_q(D).\n```\n\nBecause the full group is used and the same deterministic pipeline is evaluated on every orbit member,\n\n```math\n\frac1{|S|}\sum_{\pi\in S}e(D^\pi)=1\n```\n\nexactly. In production the conditioning state is also part of the definition of \(W\): the Genesis journal is snapshotted once before orbit evaluation, every orbit call reads that same snapshot, all calls use `journal_write=False`, and the live/frozen journal digests must be unchanged after the orbit.\n\nFor fresh epochs \(D_t\), if conditional group invariance holds under the target null,\n\n```math\n\mathbb E_0[e_t\mid\mathcal F_{t-1}]\le1,\qquad E_t=\prod_{i=1}^t e_i.\n```\n\nThe software records the resulting process per target. At \(\alpha=0.05\), \(E_t\ge20\) is a per-target Ville crossing only; no system-wide error guarantee is claimed. A global online multi-target e-value controller remains `UNIMPLEMENTED`.\n\nImplementation calibration uses 1000 independent C6 noise paths with three fresh epochs each; 15 paths cross 20. This empirical rate is a sanity check, not the mathematical proof. The S6 identity-max fixture is selected after exhaustive orbit inspection and reoriented to identity solely to demonstrate the \(|S|\) resolution ceiling; it is not prospective power evidence.\n

# 15.21.0 — математическая модель 655-осевого coverage/void scan

## 15.21.1 Каноническое пространство

Пусть текущий реестр канонических осей

```math
A=\{a_1,\dots,a_n\},\qquad n=655.
```

Atlas не интерпретирует множество осей как требование использовать все координаты одновременно. Исследовательским объектом является конечное подмножество

```math
S\subset A,\qquad 2\le |S|<\infty,
```

а общий потенциальный зарегистрированный subset-space равен

```math
|\mathcal P(A)\setminus\{\varnothing\}|=2^{655}-1.
```

Для пар и троек текущего реестра:

```math
\binom{655}{2}=214185,\qquad
\binom{655}{3}=46620935.
```

Это combinatorial address space, а не число доказанных физических отношений.

## 15.21.2 Coverage как навигационная величина

Для материализованного frontier `F` определим частоту участия оси

```math
c_1(a)=\sum_{S\in F}\mathbf 1[a\in S].
```

Zero-coverage set:

```math
Z(F)=\{a\in A:c_1(a)=0\}.
```

До 15.21.0:

```math
|Z(F_{before})|=285.
```

После finite-release coverage witnesses внутри существующего `CandidateGenerationPipeline/6.27.0`:

```math
\boxed{|Z(F_{15.21})|=0}.
```

Это не доказательство полноты. Для unordered pairs

```math
c_2(a_i,a_j)=\sum_{S\in F}\mathbf 1[\{a_i,a_j\}\subseteq S]
```

и наблюдаемое покрытие

```math
C_2=|\{\{a_i,a_j\}:c_2(a_i,a_j)>0\}|=6780,
```

то есть

```math
\rho_2=\frac{6780}{214185}=0.031654877793.
```

Для cross-domain pairs:

```math
C_2^{cross}=4056,\qquad
N_2^{cross}=183996,
```

```math
\rho_2^{cross}=\frac{4056}{183996}=0.022043957477.
```

Следовательно, правильная интерпретация:

```math
\boxed{c_1(a)>0\ \forall a\in A\ \not\Rightarrow\ \text{space exhausted}.}
```

## 15.21.3 Fair-dovetail + finite-release void witnesses

Asymptotic owner сохраняет append-only birth order и starvation-resistant traversal. Его научные потолки остаются

```math
K_{axis}=K_{pair}=K_{node}=K_{global}=\varnothing.
```

Finite-release witness не заменяет dovetail. Он лишь материализует наблюдаемый void:

```math
c_1(a)=0\Rightarrow \operatorname{nominate}(a,S_{semantic}),
```

где `S_semantic` выбирается из уже зарегистрированных семантически совместимых координат. Witness получает статус исследовательского кандидата и проходит тот же единый U0–U10 путь, что и любой другой frontier record.

Чтобы witness не искажал будущую маршрутизацию, статистика `least-visited` вычисляется по earned historical traversal, а созданные текущим release structural witnesses не становятся собственным критерием отбора при replay. Это обеспечивает стабильность deterministic replay.

## 15.21.4 Конкурирующие гипотезы

Для каждого adaptive subspace `S` materialized candidate теперь хранит фиксированный набор из семи явно различимых альтернатив

```math
\mathcal H(S)=\{H_0,H_1,\dots,H_6\},\qquad |\mathcal H(S)|=7.
```

`H_0` — null/lower-order/projected explanation; `H_1...H_6` — фиксированные шаблоны mechanism-family. Они задают одинаковый семействовый каркас для каждого пространства и **не являются семью независимо выведенными физическими механизмами**. Поэтому число строк ниже является размером bookkeeping enumeration, а не мерой научного evidence. При 3,706 пространствах:

```math
\sum_{S\in F}|\mathcal H(S)|=3706\times7=25942.
```

Наличие альтернатив не является подтверждением ни одной из них. Фальсифицирующий эксперимент должен максимизировать различимость хотя бы двух preregistered alternatives и пройти обычные U5–U9 gates.

## 15.21.5 Axis lifecycle

Новая координата не становится canonical по факту генерации. Lifecycle:

```math
\text{PROPOSED}
\rightarrow\text{RESEARCH}
\rightarrow\text{WORLD-ATTESTED / MODEL-DISCOVERED}
\rightarrow\text{OOD}
\rightarrow\text{REPLICATION}
\rightarrow\text{FALSIFICATION-GATED}
\rightarrow\text{CANONICAL}.
```

Авторитетом остаётся `DYNAMIC-AXIS-PROMOTION/8.0.0`. В 15.21.0 централизованы 11 существовавших research-local proposals, но число новых canonical promotions равно нулю. Это fail-closed поведение: отсутствие world-attestation сохраняет proposal как `UNKNOWN/RESEARCH`, не как FALSE и не как canonical fact.

## 15.21.6 Unified scientific depth

Текущий gate census:

```math
(U_0,U_1,U_2,U_3,U_4,U_5,\ldots,U_{10})
=(4106,604,447,447,447,0,0,0,0,0,0).
```

447 U4-survivors получают полный computable evidence-acquisition portfolio U5–U10. Portfolio decomposition:

```math
447=286_{single-domain}+161_{cross-domain}.
```

Ни coverage witness, ни formal U4 independence, ни отсутствие найденного prior art не дают научной promotion. Promotion остаётся разрешённой только после world-evidence gates существующего `ScientificPromotionCore/9.2.0`.

## 15.21.7 Состояние знания после scan

```math
\boxed{
655\ canonical\ axes
\rightarrow3706\ adaptive\ spaces
\rightarrow25942\ explicit\ alternatives
\rightarrow447\ U4\ materializations
\rightarrow0\ U5
\rightarrow0\ laws\ promoted
}
```

Оставшийся frontier математически огромен: полный triple census в этом release намеренно не объявляется выполненным. Следующий исследовательский шаг должен использовать pair/triple/higher-order void density, semantic compatibility и discriminating-experiment value, а не количество уже созданных кандидатов как цель само по себе.



## 15.21.8 Exact candidate → dataset → measurement binding

Пусть замороженный кандидат задаётся

```math
C=(A_C,O_C,H_C),
```

где `A_C` — множество canonical axis IDs, `O_C` — source-owner IDs, `H_C` — digest-bound typed hypothesis. Dataset IR задаётся

```math
D=(S_D,Q_D,V_D),
```

где `S_D` — exact source-family IDs, `Q_D` — canonical quantity IDs, а `V_D` — field-level observable descriptors с digest-bound selectors и value digests.

Для owner `o` определим scientific coordinate set `A(o)`, provenance source families `S(o)` и quantity vocabulary `Q(o)`. Точная dataset-compatible axis coverage требует

```math
\forall a\in A_C\;\exists o\in O_C:\quad a\in A(o)\land S(o)\cap S_D\neq\varnothing.
```

Измеримый overlap требует

```math
\exists o\in O_C:\quad S(o)\cap S_D\neq\varnothing\land\left(Q(o)\cap Q_D\setminus Q_{generic}\right)\neq\varnothing,
```

где текущий generic exclusion содержит `QTY-DIMENSIONLESS`, чтобы одно лишь наличие безразмерной координаты не создавало ложную измерительную связь.

Fail-closed data-binding indicator:

```math
B(C,D)=I_{digest}(C,H_C,D)\,I_{axis}\,I_{source}\,I_{quantity}\,I_{protocol}.
```

Но

```math
\boxed{B(C,D)=1\;\not\Rightarrow\;W(C,D)=1\;\not\Rightarrow\;U_5=PASS}.
```

`B=1` означает только, что candidate semantics можно адресовать в данном dataset без fuzzy matching. Для исполнения эксперимента дополнительно требуется preregistered response projection

```math
R_C\subseteq V_D,\qquad R_C\neq\varnothing,
```

замороженная **до confirmatory execution**. Если `R_C=∅`, статус обязан быть `DATASET_BINDING_QUALIFIED_EXPERIMENT_RESPONSE_PROJECTION_PENDING`. Выбирать response постфактум из dataset и затем считать его подтверждающим evidence запрещено.

### Daya Bay control

`SCIENTIFIC-DATA-INGESTION/5.10.0` экспортирует восемь exact descriptors из официального digest-bound Daya Bay analysis artifact. Все selectors проверяются по точному archive member + NPZ record field или YAML path; observable values представлены value digests.

Для аэродинамического кандидата

```math
C_a=\{\texttt{atmosphere\_model},\texttt{dynamic\_viscosity}\}
```

получено `B(C_a,D_{DB})=0` из-за отсутствия source-family overlap. Для metrology candidate `SUBSPACE-0F7BCAA86B7AFED82840` существующий owner `REACTOR-COVARIANCE-LIKELIHOOD` обеспечивает exact Daya Bay provenance и `QTY-COUNT`, поэтому `B=1`, но `R_C=∅`; следовательно эксперимент ещё не исполним и U5 остаётся 0.

### Epistemic consequence

Главный результат диагностики — локализация блокера:

```math
\text{generation}\;\checkmark\;\to\;\text{semantic data binding}\;\checkmark\;\to\;\boxed{\text{response projection}}\;\to\;\text{execution}\;\to\;\text{WORLD/U5}.
```

Текущее состояние намеренно оставляет `world_attestations=0`: отсутствие WORLD-tier trust/attestation нельзя исправлять искусственной записью.



# 15.22.0 — математическая модель frozen response projection и executable measurement

## 1. Почему data binding недостаточен

Пусть `C` — materialized Atlas candidate, `H_C` — его digest-bound typed hypothesis, а `D` — квалифицированный `ExperimentDataIR`. После 15.21 возможен точный semantic binding

```math
B(C,D)\in\{0,1\}.
```

Но условие `B(C,D)=1` означает только совместимость научных координат, source-family и измеримых quantities. Оно не определяет, **какой именно response должен быть вычислен**, и поэтому не задаёт исполнимый confirmatory contract.

## 2. Декларативный response descriptor

Для dataset `D` вводится конечный каталог разрешённых response projections

```math
\mathcal R_D=\{
ho_j\},\qquad

ho_j=(o_s,e,\omega,q_R,k_R,Q_{in}),
```

где `o_s` — source owner, `e` — существующий execution owner, `ω` — его операция, `q_R` — canonical quantity результата, `k_R` — exact response key, `Q_in` — набор необходимых входных canonical quantities. Descriptor не содержит наблюдаемого результата.

Для Daya Bay текущий descriptor:

```text
rho = DAYABAY-CNP-PROFILE-CHI2
source owner     = REACTOR-COVARIANCE-LIKELIHOOD
execution owner  = DAYA-BAY-FULL-LIKELIHOOD
operation        = FIT_PUBLIC_DATA_PROFILE
response         = QTY-CHI-SQUARED / chi2
required input   = QTY-COUNT
```

## 3. Prefreeze

До вычисления response Atlas обязан заморозить receipt

```math
P=\operatorname{Freeze}(C,H_C,B,D,
ho),
```

причём

```math
P.y_R=
arnothing,\qquad
P.digest=\operatorname{SHA256}(C_d,H_d,B_d,D_d,
ho_d,M).
```

`M` — executable measurement contract. В нём зафиксированы executor/operation, input observable IDs и их value digests, response quantity/key, protocol и required controls. Если response уже известен в момент freeze, contract fail-closed. Это защищает от post-hoc выбора статистики.

## 4. Исполнение

Только после валидного `P` разрешено

```math
y_R=E_{
ho}(D),
```

где `E_ρ` — заранее объявленный domain owner. Исполнение обязано повторно проверить текущий `ExperimentDataIR` digest и digest measurement contract. Для текущего Daya Bay replay:

```math
\chi^2_{\mathrm{CNP}}=595.1908738041352,\qquad

u=518,\qquad

rac{\chi^2}{
u}=1.149017130896014.
```

Этот результат является reproducible dataset/likelihood response, но **не** candidate test.

## 5. Что требуется для научной дискриминации

Нужен отдельный lowering operator

```math
\Lambda:(H_C,D_{context})\mapsto \widehat y_C
```

или, в общем случае, predicted observable field `\widehat{\mathbf y}_C`. Затем до reveal должен быть объявлен discriminating statistic

```math
T_C=T(y_R,\widehat y_C,\Sigma,\mathcal H_{alt}),
```

где `Σ` — uncertainty/covariance structure, `H_alt` — замороженные конкурирующие механизмы. Только наличие `y_R` без `\widehat y_C` не вычисляет `T_C`.

Поэтому текущая логика gates:

```math
\boxed{
B=1\land P_{frozen}=1\land E=1
ot\Rightarrow U5
}
```

и текущий более полный необходимый путь:

```math
U5\Rightarrow
B=1\land P_{frozen}=1\land E=1\land\Lambda(H_C)\;	ext{defined}\land T_C\;	ext{predeclared}\land W\;	ext{qualified}.
```

Здесь `W` обозначает требуемый WORLD/evidence trust path, а не просто наличие опубликованного файла.

## 6. Текущее эпистемическое состояние

```text
|A_canonical| = 655
|C_active|    = 4106
U4            = 447
B qualified   = 1
P frozen      = 1
E executed    = 1
Lambda ready  = 0
scientific discrimination = 0
WORLD         = 0
U5            = 0
```

Следующий математический frontier — не генерация новых `C`, а построение typed lowering `Λ` для уже существующего U4-кандидата с сохранением dimensional/convention/owner semantics и с конкурирующими forward predictions.


---

# XXIII. CURRENT 15.23.0 — один ручной lowering и held-out OOD-проверка

## 1. Цель этапа

15.23.0 не увеличивает множество кандидатов и не меняет canonical axis registry. Этап проверяет существование первого звена

```math
\boxed{H_C \xrightarrow{\Lambda_C} \widehat y_C}
```

для одного уже существующего U4-кандидата `SUBSPACE-0F7BCAA86B7AFED82840`. `\Lambda_C` здесь является **однократным ручным precommit**, а не общим алгоритмом для класса кандидатов.

## 2. Precommit до held-out reveal

До чтения held-out target counts заморожены:

```math
D_{disc}=\{6AD\},\qquad
D_1=\{8AD\},\qquad
D_2=\{7AD\},
```

```math
\theta^*=(\sin^2 2\theta_{13},\Delta m^2_{32},s_1,\ldots,s_{26})
=\arg\min_{\theta}\chi^2_{CNP}(D_{disc};\theta),
```

после чего для каждой held-out траектории вычисляется фиксированный вектор

```math
\widehat y_j=F_{DB}(D_j;\theta^*),\qquad j\in\{1,2\},
```

без refit параметров или source nuisance на `8AD`/`7AD`.

Precommit digest:

```text
c6f7880a3fc2778a942cbe6f0dfc1d97438b51649ba70941bcc9ef0fd827deea
```

Frozen lowering receipt:

```text
23d99e3bae0042ad7d6cf6bec863e02add707727d74ac480209e37caff26fc38
```

Замороженные predicted-count digests:

```text
8AD  32b65c83ca92fc5b5a767f0ba343836d8cd91d13318e9925ecff9ae86c551717
7AD  d3366847ff76708ad4a65d127d0eb72c240074ebbb9d582058dafee05b67865c
```

## 3. Preregistered collapse statistic

Для каждой траектории

```math
r_j=\frac{\chi^2_j}{\nu_j},\qquad
\sigma_j=\sqrt{\frac{2}{\nu_j}}.
```

Предварительно объявлен индивидуальный критерий

```math
\boxed{|r_j-1|\le 1.96\sigma_j}
```

и межтраекторный критерий

```math
\boxed{|r_1-r_2|\le1.96\sqrt{\sigma_1^2+\sigma_2^2}}.
```

Поскольку held-out refit запрещён, `\nu_j` равен числу held-out observation bins.

## 4. Результат после reveal

```text
8AD: chi2 = 559.0510435090229, ndf = 208,
     reduced chi2 = 2.687745401485687,
     z from unit reduced chi2 = 17.211693472304013

7AD: chi2 = 490.3941688382487, ndf = 182,
     reduced chi2 = 2.6944734551552125,
     z from unit reduced chi2 = 16.16424654632976

cross-partition z = 0.04687157070055143
```

Следовательно,

```math
\text{cross-partition consistency}=1,
\qquad
\text{absolute collapse}=0.
```

Обе независимые held-out траектории дают практически одинаковый уровень ошибки, но обе находятся далеко за заранее объявленной 95%-полосой относительно `r=1`.

Это означает

```math
\boxed{\Lambda_C\ \text{вычислима, но данный ручной lowering не проходит OOD collapse}.}
```

Это **не** означает `H_C=false`: tested object на этом этапе — конкретное отображение `\Lambda_C`, а исходный U4 candidate остаётся более общей typed relational structure без frozen scalar equation.

## 5. Эпистемическая граница

```math
\boxed{
\text{manual lowering}=1,
\quad
\text{heldout check}=1,
\quad
\text{collapse pass}=0,
\quad
WORLD=0,
\quad
U5=0.
}
```

После reveal запрещено заменять `\Lambda_C` более удобным отображением и считать новый вариант продолжением того же confirmatory test. Любой новый lowering обязан иметь новый precommit/digest и новый статус exploratory/independent test согласно источнику данных.

### 5.1. Multiplicity / alpha ledger для повторных lowering

Пусть для одного кандидата рассматривается последовательность различных precommitted lowering \(\Lambda_{C,1},\Lambda_{C,2},\ldots\). После первого reveal перебор новых отображений до успеха является множественным тестированием. Поэтому любой **второй и последующий** distinct lowering обязан до reveal объявить family budget \(\alpha_C^{tot}\), debit предыдущих попыток \(a_1,\ldots,a_{k-1}\) и debit новой попытки \(a_k>0\) так, чтобы

```math
\boxed{\sum_{i=1}^{k} a_i\le \alpha_C^{tot}.}
```

Система не назначает постфактум «удобную» стоимость уже выполненному первому тесту. Вместо этого новый retry блокируется, пока его precommit явно не укажет debit всех предшествующих попыток и правило распределения alpha. Это fail-closed защита от `retry-until-lucky`; повтор того же digest является replay, а не новой попыткой.

## 6. Структурный lowerability audit всех 447 U4-кандидатов

До обращения к данным можно проверить только структурную часть \(O_F,R_A\). В authoritative `LawSpaceRuntime.catalog` для каждого U4-кандидата проверены его `source_owner_ids`, `scientific_coordinate`, parsed formula и declared observables. Используются два уровня:

```math
S_{strict}(H)=1\iff\exists O_F:\; A(H)\subseteq A(O_F)\land F(O_F)\land Obs(O_F),
```

где один owner покрывает **все** оси кандидата, и более слабый compositional уровень

```math
S_{comp}(H)=1\iff A(H)\subseteq\bigcup_i A(O_i)\land\exists i:F(O_i)\land Obs(O_i).
```

Получено:

```text
U4 candidates                                  447
S_strict: one forward owner covers all axes     14
S_comp only: several owners required            286
full axis mapping but no forward owner             9
forward owner exists but mapping incomplete      134
no forward owner / no complete mapping             4
```

Следовательно,

```math
\boxed{14/447=3.13\%}
```

имеют строгий one-owner forward path, а

```math
\boxed{(14+286)/447=67.11\%}
```

лишь структурно адресуемы в более слабом compositional смысле. Второе число **не означает**, что для 300 кандидатов уже существует численный lowering: для 286 из них ещё отсутствует frozen owner-composition contract. Оставшиеся 147 кандидатов уже на этом этапе имеют явный structural lowering gap. Данные, target values и fit quality в этом аудите не использовались.

Этот census является `DIAGNOSTIC_PROPOSAL_NOT_GLOBAL_GATE`: он показывает, где следует усилить U1–U2 admission, но 15.23.0 ещё не переписывает глобальные promotion gates на основании одного класса анализа.

## 7. Lowerability metadata как кандидат на будущий U1–U2 admissibility contract

Один пример показывает минимальный набор структуры, без которой typed candidate нельзя честно опустить до наблюдаемой:

```math
\mathcal L(H)=\{
O_F,\ R_A,\ Q_{pred},\ D_{disc},\ D_{hold},\ N_{freeze},\ U,\ T,\ \tau,\ d_{pre}
\},
```

где `O_F` — forward owner, `R_A` — axis→forward-role map, `Q_pred` — prediction quantity, `D_disc/D_hold` — partition contract, `N_freeze` — nuisance freeze, `U` — uncertainty owner, `T,τ` — statistic/threshold, `d_pre` — no-target-value precommit digest.

В 15.23.0 это **диагностическое предложение**, а не новый глобальный gate:

```math
\boxed{\text{U1/U2 lowerability enforcement}=0.}
```

Нужны дополнительные ручные примеры разных классов кандидатов, прежде чем переносить `\mathcal L(H)` в обязательный admission contract.

## 8. Текущее состояние

```text
canonical axes                         655
active candidates                     4106
adaptive spaces                       3706
U4                                     447
exact dataset binding                    1
frozen response projection               1
executed dataset response                1
strict single-forward-owner candidates  14
composable multi-owner candidates       286
structurally addressable union          300
structurally partial/blocked            147
manual candidate lowering                1
held-out prediction check                1
manual lowering collapse passes          0
mechanism-discriminating measurements    0
WORLD attestations                       0
U5                                       0
automatic law promotions                 0
```

## 9. Два фронтира и экспериментально-зависимая мощность prediction-space

Диагностика 15.23.0 требует различать два множества исследовательского состояния:

```math
\boxed{\mathcal F_{disc}\neq\mathcal F_{emp}.}
```

`Discovery Frontier` остаётся открытым для новых осей, cross-domain комбинаций и кандидатов даже при отсутствии текущего measurement technology. Отсутствие measurement route не делает такой кандидат ложным.

`Empirical Frontier` содержит только кандидаты, для которых структурно существует путь

```math
H\rightarrow O_F\rightarrow R_A\rightarrow \widehat y\rightarrow O\rightarrow D.
```

Здесь проверяется существование отображения, а не значение target-data, поэтому сама структурная проверка lowerability не является selection по качеству fit.

Для конкретного experiment/data contract `D` вводится measurement-equivalence relation

```math
H_i\sim_D H_j
\iff
S_\Lambda(H_i;D)=S_\Lambda(H_j;D)
```

с lowering signature

```math
S_\Lambda(H;D)=
(O_F,R_A,Q_{pred},R_{resp},\Pi_H,D),
```

где `\Pi_H` — физически фиксированный prediction operator. Тогда

```math
\boxed{N_P(D)=|\mathcal H/\!\sim_D|}
```

есть число **экспериментально различимых prediction classes на данном контракте**, а не внутреннее свойство портфеля. Поэтому запись `N_P=1` запрещена без указания `D`.

Формальное различие двух `\widehat y` само по себе не создаёт новый класс. Для классов `i,j` требуется preregistered distinguishability condition, например

```math
\boxed{
\Delta_{ij}(D)=
\|\widehat y_i-\widehat y_j\|_{\Sigma_D^{-1}}
>\tau_D,
}
```

где `\Sigma_D` и `\tau_D` объявлены до просмотра результата. Таким образом добавление нефизического свободного параметра в lowering не должно увеличивать `N_P(D)`.

На текущей доступной Daya Bay/DLR measurement surface результаты 15.23.0 дают диагностическую воронку

```text
U4 candidates                         447
structurally addressable              300
single-forward-owner                   14
exactly dataset-bound                   6
unique executable prediction classes    1
```

то есть

```math
\boxed{N_P(D_{available})=1}
```

для **текущего** набора исполнимых Daya Bay/DLR contracts. Это не утверждение о будущем эксперименте `D'`: возможно `N_P(D')>1`.

Единственный уже исполненный класс прошёл ручной no-refit lowering `6AD -> {8AD,7AD}` и дал согласованный между независимыми held-out траекториями, но абсолютный OOD failure. Следовательно текущая эмпирическая поверхность не содержит второго независимого исполнимого маршрута, на котором можно честно повторить U5-попытку без relabeling/retry.

## 10. Measurement requests: что Atlas просит у природы

Отсутствующие наблюдаемые теперь должны фиксироваться как положительная исследовательская продукция, а не как `NO_DATA`. Текущий authoritative список находится в

`data/measurement_requests/ATLAS_MEASUREMENT_REQUESTS_CURRENT.json`.

Для DLR oLAF зафиксированы два запроса:

1. Для `AERO-LTI-PSD-PROPAGATION` необходимы `Phi_w(f)` и фаза/complex transfer `arg G_zw(f)` на совместимой сетке частот. Публичный artifact содержит magnitude anchors, но отсутствие фазы блокирует полный causal kernel.
2. Для `AERO-STATE-FEEDBACK-CONTROL` необходимы синхронные `x(t)`, frozen `K` и `u(t)` для того же прогона, чтобы проверить `u(t)=-Kx(t)` и перенести это в измеряемый response без refit.

Эти записи имеют статус `REQUESTED_NOT_AVAILABLE_IN_CURRENT_PUBLIC_ARTIFACTS`; они не являются WORLD-attestation, U5 или доказательством ложности соответствующих кандидатов.

## Query-driven research and scalar-law birth — current 15.24.0

Atlas has two distinct research modes. `Discovery Frontier` remains open-ended and may retain UNKNOWN candidates that currently lack measurements. `Query Research` is focused: a scientific question and/or an observation table defines the finite search surface for the current request. A display limit is never a multiplicity limit.

For a supplied set of dimensionful quantities \(S=\{q_1,\ldots,q_n\}\), Atlas forms the exact rational dimension matrix \(D_S\). If

\[
\dim\ker D_S=1,
\]

the primitive integer null vector \(a\) freezes the mathematical candidate

\[
\Pi_S=\prod_j q_j^{a_j}.
\]

Without a target, the candidate representation is \(\Pi_S=C\). With a measured target \(y\), the frozen representation is

\[
y=f(\Pi_S),
\]

and the unknown object is only the function \(f\), not the dimensionless coordinate. Dimensionless/categorical scientific-coordinate axes are not silently treated as physical quantities; dimensional birth projects through owner symbols to canonical `quantity_id` dimensions.

Current measured census over the unchanged 3,706 adaptive subspaces: 1,636 have at least one dimensionful projected quantity; 1,542 have at least two; 683 yield \(p=1\), but these collapse to only 14 unique \(\Pi\)-signatures. Among the 447 U4 relational candidates, 125 yield \(p=1\), collapsing to 13 unique signatures. Candidate IDs therefore do not measure mathematical diversity.

The focused observation search enumerates the finite subset surface requested by the observation schema, freezes every \(p=1\) coordinate, deduplicates by mathematical signature, ranks candidates, and reports both `candidates_examined_total` and `candidates_returned`. Permutation calibration replays the entire frozen candidate surface. Returning 10–100 hypotheses therefore does not pretend that only 10–100 hypotheses were tested.

Synthetic control reproducing §4.4 with distractor quantities recovers, without formula hint,

\[
\boxed{\Pi=L^2k/D}
\]

at rank 1 with `collapse_score = 0.1059285586`; the 100-permutation whole-surface null gives familywise empirical \(p=1/101\). This is a sensitivity/control result, not a new law.

The current `PiGenesisBridge` then searches \(f(\Pi)\) using the installed Genesis monomial/Laurent grammar. On the same control, that grammar does not recover an adequate cross-system function. A bounded rational diagnostic over \(\phi=\sqrt{\Pi}\) improves fit materially but remains insufficient for cross-system transfer. Therefore the next representation shell must be expanded in preregistered order rather than by post-result function shopping.

### Question to focused subspace

`question + named_observables` first resolves observables to canonical quantities. Bare symbols are fail-closed: a token such as `D` or `L` is rejected when it maps to more than one registered quantity. Canonical quantity IDs or a column passport resolve the ambiguity. Expansion then uses only registered owner quantity co-occurrence/bridges; target values are not read during this focusing step.

### SO WHAT contract

A frozen formula is assessed for usefulness only after birth. Candidate utility may include: cross-system collapse, parameter reduction, regime compression, predictive transfer, ambiguity removal, and a discriminating measurement specification. Relational descriptions without a frozen mathematical object do not receive scalar-law utility credit.


# CURRENT 15.25.0 — Multi-Π Query Function-Form Search

## 1. Scope and ownership

Release 15.25.0 extends the existing authoritative `QUERY-DRIVEN-RESEARCH` path; it does not create a parallel scientific search engine. The exact dimension authority remains the seven-dimensional rational kernel. The scalar `p=1` path remains unchanged. The new lane begins only after the exact kernel proves

\[
p=\dim\ker D>1.
\]

`DIMENSIONAL-SCALAR-LAW-BIRTH` still refuses to invent a scalar formula in this regime and returns `FUNCTION_FORM_REQUIRED_P_GT_1`. `QUERY-DRIVEN-RESEARCH/1.1.0` consumes that formally unresolved state when observations and a response are explicitly supplied.

## 2. Exact multi-Π coordinate construction

For quantities \(q_1,\ldots,q_n\) define the dimension matrix

\[
D=[d(q_1)\;\cdots\;d(q_n)]\in\mathbb Z^{7\times n}.
\]

Let

\[
r=\operatorname{rank}_{\mathbb Q}D,\qquad p=n-r>1.
\]

Atlas computes a rational null basis and canonicalizes it to primitive integer columns

\[
A=[a_1,\ldots,a_p],\qquad Da_j=0.
\]

The frozen coordinates are

\[
\boxed{\Pi_j=\prod_{i=1}^{n}q_i^{(a_j)_i}},\qquad j=1,\ldots,p.
\]

The basis is deterministic for receipt identity, but physics is attached to the subspace \(\ker D\), not to the claim that this basis is unique. Any invertible integer/rational recombination that spans the same null space can define an equivalent coordinate chart.

Crucially, \(A\) and every \(\Pi_j\) are frozen before any target-dependent fitting. The target cannot rotate the dimensional kernel toward a favorable representation.

## 3. Finite structural function grammar

The current query lane tests a finite structural family, not an exhaustive space of mathematics. For a subset \(S\subseteq\{1,\ldots,p\}\), let \(z_S\) be the training-standardized selected π coordinates. For total degree \(d\),

\[
\boxed{
F_{S,d}(\Pi)=\beta_0+
\sum_{1\le |\alpha|\le d}\beta_\alpha z_S^\alpha
}
\]

with multi-index \(\alpha\in\mathbb N^{|S|}\). The number of fitted coefficients including the intercept is

\[
N_{\text{term}}={|S|+d\choose d}.
\]

Only fold-feasible full-rank fits are admitted. The current deterministic schedule permits degrees 1–4 when \(p\le3\) and degrees 1–3 when \(p\ge4\). Full-manifold structures are generated before lower-dimensional subsets. A query requests between 10 and 100 structural hypotheses; this is an execution tranche only and is not a scientific ceiling on axis count, interaction order, future grammars, or the open Discovery Frontier.

Polynomial surfaces are therefore a **query representation grammar**, not the primary Atlas scientific coordinate space and not a redefinition of Atlas as symbolic regression.

## 4. Cross-validation risk

If experimental grouping is supplied and contains at least three groups, validation is leave-one-group-out. Otherwise a deterministic 3–5-fold partition is used. For every fold, standardization and all coefficients are learned from the training partition only.

Let \(\hat y_i^{(-f(i),h)}\) be the out-of-fold prediction from structural hypothesis \(h=(S,d)\). Atlas ranks by

\[
\widehat R_h=
\frac{
\sqrt{N^{-1}\sum_i(y_i-\hat y_i^{(-f(i),h)})^2}
}{s_y},
\]

where \(s_y\) is the full observed target standard deviation used only as the normalization scale. The accompanying OOF coefficient of determination is

\[
R^2_{\mathrm{OOF},h}=1-
\frac{\sum_i(y_i-\hat y_i)^2}
{\sum_i(y_i-\bar y)^2}.
\]

The winner is the smallest \(\widehat R_h\), with structural complexity used only as deterministic tie-breaking. Because the same OOF scores select the winner, the winner's CV score is **not** claimed to be an unbiased post-selection estimate of future generalization. Independent held-out or world replication remains necessary.

## 5. Whole-function-surface permutation null

Multiplicity belongs to the searched structural surface, not to the displayed shortlist. Let \(\mathcal H_Q\) be all structurally fitted hypotheses in the query tranche and define

\[
\boxed{T(y)=\min_{h\in\mathcal H_Q}\widehat R_h(y)}.
\]

For permutation \(b=1,\ldots,B\), Atlas constructs a null target \(y^{(b)}\) and reruns **every** hypothesis in \(\mathcal H_Q\), including undisplayed hypotheses:

\[
T_b=\min_{h\in\mathcal H_Q}\widehat R_h(y^{(b)}).
\]

The familywise empirical p-value is

\[
\boxed{
p_{\mathrm{FW}}=
\frac{1+\#\{b:T_b\le T_{\mathrm{obs}}\}}{B+1}
}.
\]

The smallest attainable value is

\[
p_{\min}=\frac1{B+1}.
\]

A requested level \(\alpha\) is impossible when \(p_{\min}>\alpha\); that state is `INSUFFICIENT_NULL_RESOLUTION`, never PASS.

With explicit validation groups, 15.25.0 uses `WITHIN_VALIDATION_GROUP`: target values are permuted inside each group, not across groups. This preserves group membership and tests the response-coordinate association conditional on the group structure. Its validity requires the explicitly recorded assumption of within-group exchangeability. If that assumption is scientifically false, a different preregistered block/orbit null is required.

## 6. Dimensional response boundary

A dimensionless predictor vector does not make a dimensional response universally comparable. The receipt distinguishes:

- `DIMENSIONLESS_TARGET`: direct dimensionless response is admissible;
- `UNKNOWN_TARGET_DIMENSION`: no universality claim is licensed from target dimensions;
- `DIMENSIONAL_TARGET_REQUIRES_RESPONSE_SCALE_FOR_UNIVERSAL_COLLAPSE`: a response normalization or dimensionless response coordinate must be predeclared before a universal-collapse claim.

Thus

\[
Y=F(\Pi_1,\ldots,\Pi_p)
\]

is a structurally meaningful regression statement for measured \(Y\), but universal dimensional similarity requires a dimensionless/scaled left-hand side.

## 7. Synthetic four-Π qualification control

The current machinery control uses the seven axes

\[
\{\tau,D,L,k,E,\eta,\rho\}
\]

with exact kernel rank 3 and nullity 4. The canonical receipt is

\[
\Pi_1=\frac{\tau D}{L^2},\qquad
\Pi_2=\tau k,\qquad
\Pi_3=\frac{\tau E}{\eta},\qquad
\Pi_4=\frac{\tau E}{\rho D}.
\]

On 240 synthetic rows arranged in six validation groups, 45 structural hypotheses are executable under the frozen degree schedule. The top structure is the full four-coordinate degree-2 manifold with 15 coefficients. The current receipt reports

\[
\widehat R_{\min}=0.01778409740297801,
\]

\[
R^2_{\mathrm{OOF}}=0.9996837258795613,
\]

and OOF RMSE

\[
0.025763492241893372.
\]

With \(B=99\) whole-surface within-group permutations,

\[
p_{\min}=p_{\mathrm{FW}}=0.01,
\]

and the median null winner has NRMSE approximately

\[
0.9986278628840136.
\]

This proves implementation sensitivity and whole-surface replay on a constructed control. It is not world evidence and establishes no physical law.

## 8. Exact replay of the five directed cross-domain kernels

The 2026-09-08 directed scans were recomputed with the exact rational kernel and reproduce:

1. Electrochemistry × flow × reaction–diffusion, \(p=3\):
   \[
   \frac{k_2cL^2}{D},\quad \frac{k_2cL}{v},\quad \frac{F\Delta\phi}{RT}.
   \]
2. Thermo-mechanics × materials × flow, \(p=4\):
   \[
   \alpha_T\Delta T,\quad \frac{E}{\rho v^2},\quad
   \frac{E\rho L^2}{\mu^2},\quad
   \frac{E}{\rho L^2\omega^2}.
   \]
3. Photochemistry × optics × quantum × diffusion, \(p=5\):
   \[
   \varepsilon\ell c,\quad \frac{\ell}{L},\quad
   \frac{\ell^2k}{D},\quad \frac{k}{\omega},\quad
   \frac{k\hbar}{k_BT}.
   \]
4. Reaction–diffusion × viscoelastic memory, \(p=4\):
   \[
   \frac{\tau D}{L^2},\quad\tau k,\quad
   \frac{\tau E}{\eta},\quad\frac{\tau E}{\rho D}.
   \]
5. Phase transition × thermodynamics × flow, \(p=4\):
   \[
   \frac{c_p\Delta T}{h},\quad
   \frac{c_p\Delta T}{v^2},\quad
   \frac{c_p\Delta T L^2}{\alpha^2},\quad
   \frac{c_p\Delta T}{P\Delta v}.
   \]

These receipts establish dimensional reproducibility only. They do not establish the unknown function \(F\), novelty, causality, applicability, or world validity.

## 9. World-data binding audit and fail-closed state

A directed literature/data audit was performed first for candidates 4 and 1. Partial experimental sources exist, but the current audit did **not** identify a single observation table in which every required axis and response is measured or independently calibrated for each specimen/run.

For candidate 4, reaction–diffusion hydrogel degradation data and active-hydrogel time series cover useful subsets, but do not jointly expose \(\tau,D,L,k,E,\eta,\rho\) per observation. For candidate 1, electrochemical-flow studies expose flow, geometry, diffusion/mass-transfer and electrochemical observables, but the inspected flow-reactor model assumes electron transfer faster than transport rather than independently identifying the required \(k_2\), and the inspected flow-battery dataset is not a direct joint table for all nine requested axes.

The release therefore records

`NO_COMPLETE_JOINT_AXIS_TABLE_IDENTIFIED_IN_CURRENT_SEARCH`

and

`U5 = UNKNOWN`.

No rows are synthesized by stitching parameter values from unrelated papers. Such stitching would erase specimen/run covariance and create a fictitious joint empirical distribution.

The preferred next experiment for candidate 4 must measure or independently calibrate all seven axes plus response \(Y\) on the same specimen/run family, then evaluate a leave-one-family-or-geometry-out transfer test with a preregistered block-preserving whole-function-surface null.

## 10. Claim boundary

15.25.0 establishes all of the following and nothing stronger:

- `p>1` is no longer silently dropped by Query mode;
- exact \(\ker D\) remains the dimensional authority;
- the π basis is frozen before fitting \(F\);
- 10–100 structural hypotheses can be searched in one finite query tranche;
- all fitted hypotheses are replayed under the permutation null;
- grouped validation/null structure is explicit;
- the same API/owner path exposes the new lane;
- five cross-domain kernels are exactly reproducible;
- no complete joint world table was identified in the current directed search;
- no multi-Π world U5 pass and no new law are claimed.


# CURRENT 15.25.0 — Executable exoplanet missing-axis birth example

## 1. Purpose and provenance boundary

The executable example at `examples/exoplanets_dimensional_birth_of_G.ipynb` demonstrates the inverse step

\[
\boxed{\text{observations}\to\text{structural exponent search}\to \mathbf d(C)\to\ker_{\mathbb Q}D}.
\]

The raw table from the historical 172-exoplanet / 132-star manuscript experiment is not present in the current distribution. Therefore that historical receipt is not silently reconstructed. The runnable release example uses a separate sealed retrospective subset of the NASA Exoplanet Archive confirmed-planets export dated 2018-03-03. Fifty rows from 38 host systems survive the pre-search completeness predicate

\[
P>0,\qquad a>0,\qquad M_\star>0.
\]

The CSV stores source row IDs and source provenance. This dataset is a worked example, not WORLD-tier prospective evidence.

## 2. Frozen structural shell

The search does not receive the symbol, value, or dimension of the gravitational constant. It observes only

\[
a:[L],\qquad P:[T],\qquad M_\star:[M].
\]

For an integer vector

\[
e=(e_a,e_P,e_M),
\]

the candidate row-wise closing quantity is

\[
C_i(e)=a_i^{e_a}P_i^{e_P}M_{\star,i}^{e_M}.
\]

The finite demonstration shell is frozen as

\[
-4\le e_a\le4,\quad -4\le e_P\le4,\quad -3\le e_M\le3,
\]

with all three exponents nonzero, primitive integer vectors only,

\[
\gcd(|e_a|,|e_P|,|e_M|)=1,
\]

and one canonical representative for the sign-equivalent pair \(e\sim-e\). Exactly 172 structural hypotheses remain. This 172 is the size of this example shell and has no relation to the historical 172-row dataset.

## 3. Data-derived closure score

For every admissible \(e\), define

\[
\ell_i(e)=e_a\ln a_i+e_P\ln P_i+e_M\ln M_{\star,i}=\ln C_i(e).
\]

The raw constancy defect is

\[
s_C(e)=\operatorname{sd}_i\ell_i(e).
\]

To compare primitive directions with different marginal variation, the notebook reports

\[
\boxed{
\rho(e)=
\frac{s_C(e)}
{\sqrt{\sum_{j\in\{a,P,M\}} e_j^2\,s_j^2}}
},
\]

where \(s_j=\operatorname{sd}(\ln x_j)\). Ranking is by \(\rho\), then deterministic complexity tie-breaks. No registry constant is read before the winner is frozen.

The observed winner is

\[
\boxed{e^*=(3,-2,-1)},
\]

with

\[
\rho(e^*)=0.008061939711222455,
\qquad
s_C(e^*)=0.04832792485093855.
\]

Thus the data-derived closing quantity is

\[
C=\frac{a^3}{P^2M_\star}.
\]

## 4. Birth of the missing dimension

Only the dimensions of the three measured coordinates are now used:

\[
\mathbf d(a)=(1,0,0,0,0,0,0),
\]

\[
\mathbf d(P)=(0,0,1,0,0,0,0),
\]

\[
\mathbf d(M_\star)=(0,1,0,0,0,0,0).
\]

Therefore

\[
\begin{aligned}
\mathbf d(C)
&=3\mathbf d(a)-2\mathbf d(P)-\mathbf d(M_\star)\\
&=(3,-1,-2,0,0,0,0),
\end{aligned}
\]

or

\[
\boxed{[C]=L^3M^{-1}T^{-2}}.
\]

This is the generated dimension. At this stage the algorithm has still not read the name `G` or its CODATA value.

## 5. Exact closure after axis birth

Return the generated coordinate to the canonical exact rational dimensional authority. For

\[
q=(a,P,M_\star,C)
\]

the augmented dimension matrix has

\[
\operatorname{rank}_{\mathbb Q}D=3,\qquad n=4,\qquad p=n-r=1.
\]

The exact null space is generated, up to sign, by

\[
(-3,2,1,1),
\]

or equivalently

\[
(3,-2,-1,-1).
\]

Hence

\[
\boxed{
\Pi=a^3P^{-2}M_\star^{-1}C^{-1}=1
}.
\]

The example imports the same `_fraction_rref/_fraction_nullspace` implementation used by the current dimensional owner rather than creating a notebook-local floating-point null-space algorithm.

## 6. Post-freeze registry identification

Only after \(e^*\) and \(\mathbf d(C)\) are frozen does the example read `data/constants/registry.json`. The generated dimension equals the registered dimension of `CONST-G`:

\[
\mathbf d(C)=\mathbf d(G)=(3,-1,-2,0,0,0,0).
\]

The dimensionless two-body normalization \(4\pi^2\) is then permitted only as post-hoc interpretation. From

\[
\widehat C=1.731527169756757\times10^{-12},
\]

the retrospective snapshot gives

\[
\widehat G_{\rm post}=4\pi^2\widehat C
=6.835795270094836\times10^{-11},
\]

compared with the local registry value

\[
G_{\rm registry}=6.67430\times10^{-11}.
\]

The relative difference is approximately \(2.420\%\). The numerical discrepancy is not hidden: the catalog values are rounded/model-derived retrospective parameters and this example is not a metrology experiment.

## 7. Cross-system diagnostic

As a non-promotional stability diagnostic, rows are partitioned into four stellar-mass quartiles. For the frozen exponent vector, the standard deviation of the four group means of \(\ln C\) is

\[
0.014356233158234628.
\]

This is reported as a diagnostic only. It is not substituted for a preregistered independent-system replication or a whole-pipeline permutation gate.

## 8. Claim boundary

The executable example establishes that the shipped code can:

1. load a sealed real exoplanet table without network access;
2. exhaust the declared 172-member primitive exponent shell;
3. freeze \((3,-2,-1)\) without consulting `CONST-G`;
4. generate \(L^3M^{-1}T^{-2}\);
5. return the new axis to the exact Atlas kernel and obtain \(p=1\);
6. identify the generated dimensional class with `CONST-G` only after freeze.

It does **not** establish an independent discovery of gravity, reproduce the missing historical 172-row manuscript table, prove that catalog parameters are mutually independent measurements, or promote any scientific claim to U5/WORLD. The complete inverse Dimensional Closure v2.0 remains a documented research workflow rather than a dedicated production owner in 15.25.0.

# CURRENT 15.26.0 — EDA Chip-Design Research Owner

## 1. Architectural boundary

Release 15.26.0 adds `EDA-CHIP-DESIGN-RESEARCH/1.0.0` as a world-interaction and design-space research owner. It does not duplicate synthesis, technology mapping, placement, clock-tree synthesis, routing, extraction, DRC, LVS, or GDS generation. Those operations are delegated to OpenROAD Flow Scripts (ORFS), with Yosys/OpenROAD/KLayout as external authoritative evaluators. Atlas owns only the frozen research space, sequential selection rule, evidence normalization, comparison protocol and claim boundary.

The first pilot fixes

\[
\mathcal X =
\{u,a,\rho,c\}
\]

with

\[
u=\mathrm{CORE\_UTILIZATION},\qquad
 a=\mathrm{CORE\_ASPECT\_RATIO},\qquad
 \rho=\mathrm{PLACE\_DENSITY},\qquad
 c=\mathrm{CTS\_CLUSTER\_SIZE}.
\]

The frozen ranges are

\[
20\le u\le 50,
\qquad 0.70\le a\le1.40,
\qquad 0.55\le\rho\le0.80,
\qquad10\le c\le60.
\]

The process/design pair is fixed before world observations:

\[
\boxed{\mathrm{sky130hd}\times\mathrm{gcd}}.
\]

The shipped external-world workflow also freezes OpenROAD Flow Scripts at Git commit

```text
be0dca0b1fd41df54792b3012350cd52bccd99bb
```

before any EDA metric is read. Changing the ORFS revision is a new world freeze, not an in-trial tuning operation.

The Halton candidate pool and the deterministic maximin common warm start are also frozen before any EDA metric is read.

## 2. World observables and feasibility

For configuration \(x\in\mathcal X\), the external EDA world returns at least

\[
A(x),\quad P(x),\quad s(x),\quad n_{\rm DRC}(x),\quad L_{\rm LVS}(x),
\]

where \(A\) is final instance area, \(P\) total power, \(s\) final worst setup slack, \(n_{\rm DRC}\) the DRC violation count, and \(L_{\rm LVS}\in\{0,1\}\) is an explicit LVS match receipt. If the SDC clock period is \(T_c\), the effective critical delay used for PPA comparison is

\[
D(x)=T_c-s(x).
\]

A configuration is feasible iff

\[
\boxed{
\mathcal F(x)=
\mathbf 1[s(x)\ge0]
\mathbf 1[n_{\rm setup}(x)=0]
\mathbf 1[n_{\rm DRC}^{\rm signoff}(x)=0]
\mathbf 1[L_{\rm LVS}(x)=1]
\mathbf 1[G_{\rm final}(x)=1]
=1.}
\]

Here \(n_{\rm DRC}^{\rm signoff}\) comes only from the explicit final DRC receipt and \(G_{\rm final}=1\) means the final GDS artifact exists. Detailed-route DRC is diagnostic and is not a substitute. A missing setup-violation count, absent/ambiguous LVS result, missing sign-off DRC receipt or absent final GDS makes the gate fail closed.

## 3. PPA objective

The dimensional product

\[
A P D
\]

is retained only as an within-design reporting metric. Search uses the dimensionless normalized objective

\[
\boxed{
J(x)=\frac13\left[
\log\frac{A(x)}{A_0}+
\log\frac{P(x)}{P_0}+
\log\frac{D(x)}{D_0}
\right],}
\]

where \((A_0,P_0,D_0)\) are medians computed only from the common preregistered warm-start observations. This prevents strategy-specific normalization and prevents a later winner from changing the scale seen by an earlier strategy.

For surrogate fitting only, infeasible or incomplete points receive a finite penalty:

\[
J_{\rm model}(x)=J(x)+8\,[1-\mathcal F(x)],
\]

and an incomplete PPA measurement receives a larger fixed sentinel. This penalty assists acquisition; it never makes an infeasible design eligible to win.

## 4. Reuse of the existing multi-dimensional Query owner

The four EDA knobs are treated as dimensionless design coordinates. Their dimensional matrix is the zero matrix, so its exact rational kernel has

\[
\operatorname{rank}D=0,
\qquad
p=4.
\]

The EDA owner does not introduce a second polynomial fitting implementation. It calls the existing `QUERY-DRIVEN-RESEARCH/1.1.0` function-form lane on

\[
J_{\rm model}=F(u,a,\rho,c).
\]

The same 10–100 structural-hypothesis contract applies. The rank-1 fitted surface supplies \(\widehat J(x)\). Atlas acquisition is

\[
\boxed{
a_{\rm Atlas}(x)=
\widehat J(x)-\lambda d(x,\mathcal O),
\qquad \lambda=0.20,}
\]

where \(d(x,\mathcal O)\) is Euclidean distance in normalized knob coordinates from \(x\) to the already observed set \(\mathcal O\). Atlas selects the unevaluated point minimizing \(a_{\rm Atlas}\). The second term is an explicit exploration pressure; it does not read hidden world values.

If the Query surface is not fit-able from the available rows, Atlas falls back to deterministic maximin geometric exploration. This is a search fallback, not a surrogate physics model.

## 5. Equal-budget baselines

All strategies receive the identical frozen warm-start set and identical per-strategy evaluation budget \(B\). Exact configurations are globally cached, so a run shared by several strategies is physically executed once while remaining available to all strategies that selected it.

The comparison set is

\[
\boxed{
\{\mathrm{Atlas},\mathrm{Random},\mathrm{Grid},\mathrm{Bayesian\ GP\!+\!EI}\}.}
\]

Random uses a sealed seed. Grid uses deterministic coverage of the same frozen pool. The Bayesian baseline uses an RBF Gaussian process

\[
k(x,x')=\exp\left[-\frac{\|x-x'\|^2}{2\ell^2}\right],
\qquad \ell=0.35,
\]

with expected improvement

\[
EI(x)=\Delta(x)\Phi(z)+\sigma(x)\phi(z),
\qquad
z=\frac{J_{\min}-\mu(x)}{\sigma(x)}.
\]

No baseline is granted more world evaluations than Atlas.

## 6. Experimental decision rule

Let

\[
R_s=\min_{x\in\mathcal O_s,\ \mathcal F(x)=1} A(x)P(x)D(x)
\]

be the best feasible raw PPA reached by strategy \(s\) under the same budget. The first pilot can report an Atlas win only if

\[
\boxed{
R_{\rm Atlas}<
\min(R_{\rm Random},R_{\rm Grid},R_{\rm Bayes}).}
\]

The comparison is defined only if Atlas, Random, Grid and Bayesian GP+EI each reach at least one fully feasible design. If any strategy has no feasible design, the experiment is `INCONCLUSIVE_MISSING_FEASIBLE_STRATEGY`; it is not converted into an Atlas win or loss. If a baseline wins in a complete comparison, that negative result is preserved. No retuning of the Atlas acquisition rule after reveal is part of the same trial.

## 7. Qualification versus silicon evidence

`qualification_oracle` is a deterministic interacting synthetic surface used only to verify software mechanics: frozen sampling, four-strategy orchestration, caching, sign-off gating and claim suppression. It is not semiconductor physics, not OpenROAD, not silicon and not evidence that Atlas improves PPA.

A chip result requires a live ORFS execution. If OpenROAD/Yosys/KLayout/Docker or the ORFS tree is absent, the authoritative state is

\[
\boxed{\mathrm{CHIP\_PILOT\_BACKEND\_UNAVAILABLE}}
\]

with `scientific_result = null`. No synthetic substitution is permitted.

The GitHub workflow `.github/workflows/atlas-chip-gcd-pilot.yml` is the external-world execution lane. It freezes ORFS to commit `be0dca0b1fd41df54792b3012350cd52bccd99bb`, runs `sky130hd/gcd` through `all`, GDS, DRC and LVS and stores all unique world-evaluation receipts together with their external-world identity. Until that receipt exists and all four strategies each have a fully feasible design, whether Atlas beats the baselines is `UNKNOWN`.

## 8. Claim boundary

15.26.0 establishes an executable, fail-closed Atlas-to-EDA research interface and benchmark protocol. It does not establish any of the following:

- that Atlas currently beats Random, Grid or Bayesian optimization on real EDA data;
- that the chosen four-dimensional search space is globally optimal or exhaustive;
- that `sky130hd/gcd` generalizes to larger ASICs, analog ICs or other PDKs;
- that one clean GDS/DRC/LVS run is sufficient for foundry tapeout;
- that the synthetic qualification landscape is physical evidence;
- that Atlas replaces Yosys, OpenROAD, KLayout, a PDK or sign-off engineering.


# CURRENT 15.27.0 — Residual-Driven Function-Language Birth

## 1. Architectural placement

Function-language birth is **not** a new scientific owner and is not a parallel optimizer. The authoritative search owner remains:

```text
QUERY-DRIVEN-RESEARCH/1.2.0
```

The language-birth mechanism is a component of the already existing Mathematical Invention Kernel:

```text
PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0
└── FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT
```

The exact rational dimension kernel remains authoritative. For a dimension matrix `D`, Atlas first computes

\[
\ker_{\mathbb Q}D=\operatorname{span}\{v_1,\ldots,v_p\}
\]

and freezes

\[
\Pi_j=\prod_i x_i^{(v_j)_i}.
\]

Function-language birth is forbidden from altering those coordinates. It changes only the executable representation in

\[
Y=F(\Pi_1,\ldots,\Pi_p).
\]

## 2. Baseline language and residual trigger

Query first fits the existing standardized total-degree polynomial grammar. Let `\hat y_i^{(-fold(i))}` be the strictly out-of-fold prediction of the selected polynomial. Then

\[
r_i=y_i-\hat y_i^{(-fold(i))},
\]

and the normalized baseline risk is

\[
R_{poly}=\frac{\sqrt{n^{-1}\sum_i r_i^2}}{\sigma_y+\epsilon}.
\]

Language birth may be considered only when

\[
R_{poly}\ge r_{birth},
\]

with current default `r_birth=0.08`. This is a search trigger, not a significance threshold.

## 3. Operation-signal diagnosis and false-birth guard

The Mathematical Invention Kernel diagnoses operation-level structure in the OOF residual rather than immediately enumerating every known family. Current probes cover reciprocal, exponential, signed-logarithmic, sinusoidal/cosinusoidal, hinge/threshold, radial/neighbourhood and low-rank latent structure.

For operation feature `\phi_m(\Pi)`, let `s_m` denote the bounded residual-association signal. The executable multiplicity-aware screen is

\[
g(n,p)=\max\!\left(g_0,\sqrt{\frac{2\log M}{n}}\right),
\]

with current proxy count approximately

\[
M\approx 7\times6\times p
\]

(and an implementation floor for small `p`). Birth requires both

\[
R_{poly}\ge r_{birth}
\]

and

\[
\max_m s_m>g(n,p).
\]

Thus high prediction error without detectable operation structure cannot force language growth. This screen is heuristic and multiplicity-aware; it is **not** a p-value and does not replace the full permutation calibration.

## 4. Generated executable languages

The finite current Query grammar can instantiate:

- `RATIONAL`: numerator/denominator response with reciprocal structure;
- `EXPONENTIAL`: finite `exp(±s z)` features;
- `LOGARITHMIC`: signed `log1p` / `log1p(z^2)` response;
- `PERIODIC`: finite Fourier `sin/cos` features;
- `PIECEWISE`: fold-local hinge/threshold features;
- `KERNEL`: radial features around deterministic training-fold centres;
- `LATENT`: training-fold low-rank projection followed by finite composition.

These names describe executable representations, not named laws and not an exhaustive ontology of mathematics. The complete Query tranche remains finite (`10…100` structural hypotheses); polynomial candidates are evaluated first and born languages use only remaining tranche capacity.

All data-dependent transforms are fold-local. Standardization, thresholds, RBF centres and latent bases are learned only on the training fold. For rational candidates an unsafe near-zero fitted denominator makes the prediction undefined; Atlas fails closed rather than clipping it into an apparently valid model.

## 5. Dynamic whole-procedure permutation null

Because the hypothesis set may now depend on residual structure, denote the complete generated surface by

\[
\mathcal H(y).
\]

The observed statistic is

\[
T_{obs}=\min_{h\in\mathcal H(y)}\widehat R_h(y).
\]

For each admissible permutation `b`, Atlas repeats the complete adaptive procedure:

\[
y^{(b)}\rightarrow\mathcal H(y^{(b)})\rightarrow
T_b=\min_{h\in\mathcal H(y^{(b)})}\widehat R_h(y^{(b)}).
\]

The familywise empirical probability remains

\[
p_{FW}=\frac{1+\#\{b:T_b\le T_{obs}\}}{B+1}.
\]

It is therefore invalid to birth a language once on the observed target and then permute only coefficients. Polynomial fitting, OOF residual diagnosis, optional birth and complete born-surface fitting are all replayed under every permutation. Grouped datasets retain their explicitly declared exchangeability scheme.

## 6. Selection and scientific boundary

The selected CV score ranks hypotheses on the supplied table but is not an unbiased post-selection estimate of generalization. Independent sealed regimes, independent systems or prospective observations remain necessary for stronger claims. Function-language birth changes the representation layer; it cannot by itself advance WORLD/U5.

## 7. Qualification controls

Current deterministic controls record:

\[
R_{periodic,poly}=0.9664343038,\qquad R_{periodic,born}=0.1318549809,
\]

an OOF reduction of about `86.36%`, and

\[
R_{kernel,poly}=0.8005488276,\qquad R_{kernel,born}=0.3230947799,
\]

an OOF reduction of about `59.64%`.

The pre-existing four-Π viscoelastic-memory polynomial control remains unchanged: `CV NRMSE=0.0177840974`, no language is born, and the established 45-hypothesis polynomial surface is preserved.

For pure noise,

\[
s_{max}=0.1487225326<g=0.2067586902,
\]

so no language is born despite baseline NRMSE near one. The permutation qualification separately verifies that the data-dependent birth procedure is replayed inside every null permutation.

## 8. Current scientific status

These controls establish executable representation sensitivity and false-birth protection only. They do not establish mathematical novelty, universal optimizer superiority, a physical law or real-world replication. The active census remains `4106` frontier candidates, `447` U4 hypotheses and `U5=0`; incomplete world measurements remain `UNKNOWN`, not false.


# CURRENT 0.15.28.0 — Adaptive Confidence, Exploration Sandbox and Hypothesis Council

The scientific problem addressed by this layer is asymmetric evidence quality. A 12-point exploratory relation and a 10,000-point precision campaign should not be discarded or promoted by the same *research-routing* policy. The strict scientific promotion contract, however, must remain invariant. Atlas therefore separates three objects:

\[
\text{evidence quality routing},\qquad
\text{research priority},\qquad
\text{scientific promotion}.
\]

Only the third belongs to `SCIENTIFIC-PROMOTION-CORE`.

## Data-quality coordinate

For measured values `y_i` with declared standard uncertainties `sigma_i`, the fallback relative uncertainty is the median sigma divided by a robust signal scale based on IQR, standard deviation and absolute median. If no uncertainty is declared, Atlas does not infer precision from sample size; the record is routed as exploratory.

The information-density coordinate is deliberately saturating in `n`, because doubling already-large datasets does not compensate for uncontrolled systematics. Uncertainty attenuates the coordinate multiplicatively. This coordinate supplies the `quality_tag` but is not interpreted as probability of correctness.

## Three epistemic routes

`STRICT` is the only quality tier eligible for the complete canonical promotion route. `EMPIRICAL` creates a phenomenological passport for meta-analysis. `EXPLORATORY` preserves variable structure as an anomaly and prevents automatic U4 entry. Thus scarce data can remain scientifically visible without being mislabeled as evidence for a law.

## Discovery Probability Index

DPI aggregates accuracy, simplicity, cross-consistency and familywise-error risk only to order the scientist's attention. The 3-D visualization coordinates are intentionally separate from the DPI formula: accuracy / simplicity / uniqueness form a landscape, while cross-consistency and FWER modify the ranked priority. A visually attractive point can therefore remain low-priority if it lacks replication or multiplicity control.

## What-if experiment generation

A rejected candidate is more useful when Atlas can state what evidence is missing. The current implementation does not invent apparatus physics; it operates on declared observed and target ranges, sensitivity and uncertainty. It identifies uncovered edges and proposes a finite set of measurements. Later owners may replace this heuristic with information-gain experiment design when a generative likelihood is available.

## Hypothesis Council

The Council records human scientific intuition without allowing it to rewrite machine evidence. Expert actions have explicit effects. Sponsorship means *re-open the evidence-acquisition path*. A dimension exception means *permit exploratory traversal under a disputed metrology mapping*. Linking weak ideas means *create a new search seed*. None is a scientific gate pass.

Repeated expert decisions can recalibrate sandbox ranking weights. To reduce immediate confirmation bias, no recommendation is produced before eight labeled decisions, changes are returned as a recommendation, and explicit application affects the external sandbox state only. The strict promotion parameters remain immutable under this mechanism.

This separation is the mathematical reason the 0.15.28.0 patch can retain weak empirical structure without weakening the scientific firewall.

# CURRENT 0.15.28.0 — Blind incompressible continuum / Navier—Stokes recovery benchmark

## 1. Цель математического контроля

Контроль проверяет способность текущего Adaptive Research Kernel восстановить локальный динамический баланс из данных без передачи именованного закона. Физическая модель используется только reference-world generator'ом и post-freeze verifier'ом.

Для двумерного несжимаемого ньютоновского reference world контрольная модель имеет вид

\[
\partial_t u + u\,\partial_xu+v\,\partial_yu
= -\rho^{-1}\partial_xp+\nu\Delta u,
\]

\[
\partial_t v + u\,\partial_xv+v\,\partial_yv
= -\rho^{-1}\partial_yp+\nu\Delta v,
\]

\[
\partial_xu+\partial_yv=0.
\]

Эти выражения **не передаются** `AdaptiveResearchKernelOwner`.

## 2. Blind coordinate map

Каждый импульсный канал передаётся как скалярная задача с общей размерностью

\[
[r_0]=[a_{07}]=[a_{12}]=[a_{19}]=[a_{23}]=L\,T^{-2}.
\]

До freeze активны только

\[
\{a_{07},a_{12},a_{19}\},
\]

а

\[
\{a_{23},a_{31},a_{37}\}
\]

являются наблюдаемыми dormant coordinates. `a31` и `a37` специально имеют ту же физическую размерность, поэтому размерностная совместимость сама по себе не может выбрать правильную ось.

Post-freeze decoder устанавливает соответствие

\[
a_{07}\leftrightarrow u\partial_x u,\qquad
 a_{12}\leftrightarrow v\partial_y u,
\]

\[
a_{19}\leftrightarrow \rho^{-1}\partial_xp,\qquad
 a_{23}\leftrightarrow \nu\Delta u
\]

для первой компоненты и аналогичное соответствие для второй.

Искомая замороженная маскированная структура therefore is

\[
 r_0=-a_{07}-a_{12}-a_{19}+a_{23}.
\]

## 3. Почему используется несколько exact-flow families

Один exact solution обычно не идентифицирует все коэффициенты. Например, в затухающем сдвиге нелинейные и pressure coordinates равны нулю, а в жёстком вращении time/diffusion channels равны нулю. Поэтому контроль объединяет четыре режима:

\[
\mathcal D = \mathcal D_{periodic}\cup\mathcal D_{rotation}\cup\mathcal D_{shear}\cup\mathcal D_{channel}.
\]

Их совместная матрица дизайна разрушает основные вырождения и позволяет независимо определить знаки и масштабы четырёх членов. Discovery rows перемешиваются детерминированным SHA-256 ordering, чтобы внутренний 70/30 split ядра содержал разные режимы.

## 4. Residual-driven adaptive-cardinality axis activation

Начальная гипотеза строится в пространстве активных координат. Если её held-out NRMSE превышает tolerance, Atlas строит residual evidence и оценивает dormant coordinates. Для множества доступных осей (D) ядро проверяет discovery-only подмножества (S\subseteq D) по мощности (1,\ldots,|D|). Выбирается минимальная мощность, для которой модель идентифицируема и

\[
\operatorname{NRMSE}_{holdout}(S)\le\varepsilon_{fit}.
\]

Если fit gate не достигнут, сохраняется только лучшее действительно улучшающее research-local подмножество. Поэтому `AXIS_BIRTH_CARDINALITY=ADAPTIVE`, `MULTI_AXIS_BIRTH=ALLOWED`, а фиксированного числа осей на цикл нет. Sealed OOD evidence не участвует в выборе. В masked-term контроле минимальная мощность остаётся равной единице: выбирается `a23`.

После активации ожидается безразмерный коэффициентный вектор

\[
(c_{a07},c_{a12},c_{a19},c_{a23})=(-1,-1,-1,+1)
\]

с нулевым intercept в пределах численной точности.

## 5. Sealed OOD protocol

Sealed rows строятся с параметрами reference world, отсутствующими в discovery set. Freeze выполняется до post-freeze semantic decoding. В acceptance criterion используется

\[
\operatorname{NRMSE}_{sealed}<10^{-10}
\]

для обеих momentum components. Это проверяет перенос найденной структуры на новый диапазон параметров внутри того же reference-world class.

## 6. Incompressibility closure lane

Отдельный blind lane использует две маскированные величины размерности `T^-1`:

\[
[c_{05}]=[c_{11}]=T^{-1}.
\]

Контроль ожидает рождение

\[
c_{05}=-c_{11},
\]

которое post-freeze соответствует локальному zero-divergence closure.

## 7. Claim boundary

Даже идеальное численное восстановление benchmark'а устанавливает только:

- корректное исполнение Atlas-native research cycle;
- восстановление структуры известного controlled reference world;
- residual-driven выбор dormant coordinate set адаптивной мощности;
- перенос на sealed parameter holdout.

Оно не устанавливает:

- существование и гладкость трёхмерных решений Навье—Стокса;
- новый физический закон;
- мировую новизну;
- универсальную способность ядра открывать произвольные PDE из необработанных полей.

## 8. Снятое архитектурное ограничение

Ограничение single-axis activation снято интегрированным adaptive-axis patch. Текущий kernel допускает multi-axis representation birth за один цикл, но не смешивает его с причинным доказательством: `REPRESENTATION_ACTIVATED` не означает `CAUSALLY_ESTABLISHED`.

# Математическая модель коллективного эпистемического ИИ — 0.15.29.0

Эта глава является нормативной моделью owner
`COLLECTIVE-COORDINATION/1.0.0`. Пусть независимые когнитивные контуры
(c\in\mathcal C) порождают типизированные предложения

\[
p_i=(a_i,c_i,d_i,e_i,\hat I_i,q_i,k_i,r_i,g_i),
\]

где (a_i) — действие, (c_i) — источник, (d_i) — домен, (e_i) — класс
доказательства, (\hat I_i) — прогноз информационной ценности, (q_i\in[0,1])
— калибровка, (k_i>0) — стоимость, (r_i\ge0) — риск, (g_i) — конфликтная
группа. Для архитектуры (\theta) Atlas выбирает (S\subseteq\mathcal P):

\[
\widehat U_\theta(S)=\sum_{i\in S}\hat I_iq_i^{\gamma_\theta}
+B_D(S)+B_E(S)-P_R(S)-P_K(S).
\]

При `HARD_FEASIBILITY` требуется (\sum_{i\in S}k_i\le B), а при
`hard_conflict_exclusion` в план не могут одновременно входить конфликтующие
действия одной группы. Эти условия — constraints, а не компоненты истины.
Search-score вычисляется только на (\mathcal W_{search}); независимый holdout
не меняет выбранную (\theta^*). Текущая транша содержит
(3\times3\times2^6=576) архитектур и не является глобальным потолком.

## Разделение представления и причинности

Для оси (a) Atlas хранит независимые эпистемические состояния

\[
R(a)\in\{\mathrm{CANDIDATE},\mathrm{REPRESENTATION\_ACTIVATED}\},\qquad
C(a)\in\{\mathrm{NOT\_ESTABLISHED},\mathrm{CAUSAL\_READY},
\mathrm{CAUSALLY\_ESTABLISHED}\}.
\]

Улучшение held-out representation допускает переход
(R(a)\to\mathrm{REPRESENTATION\_ACTIVATED}), но само по себе не изменяет
(C(a)). Поэтому

\[
\boxed{\mathrm{REPRESENTATION\_ACTIVATED}\ne
\mathrm{CAUSALLY\_ESTABLISHED}}.
\]

Residual information gain, dimensional compatibility и predictive improvement
не заменяют отдельное авторитетное причинное доказательство.

# CURRENT 0.15.29.0 — Primitive-field operator birth

## 1. Operator birth model

Второй контрольный уровень убирает готовые физические члены из входа. Atlas получает только sampled primitive fields на координатных сетках. Пусть

\[
q_0,q_1,q_2
\]

— обезличенные координаты, а

\[
f_0,f_1,f_2,f_3,f_4
\]

— обезличенные поля. По размерностям owner `PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH` определяет единственную time-like coordinate и length-like spatial coordinates. Для target field `f` он строит target

\[
T_f=D_t f
\]

не из переданной caller derivative column, а непосредственно из sampled field values.

Текущая generated grammar строит research-local acceleration coordinates вида

\[
g\,D_i f,\qquad g\,D_i^2 f,\qquad g^{-1}D_i h,
\]

только если размерность результата совпадает с `[T_f]`. Поэтому grammar типизирована, но не содержит именованных терминов `advection`, `pressure`, `viscosity` или `Navier-Stokes`.

Для контрольных dimensions

\[
[f_0]=[f_1]=LT^{-1},\quad [f_2]=ML^{-1}T^{-2},\quad [f_3]=ML^{-3},\quad [f_4]=L^2T^{-1}
\]

для каждого momentum target рождается восемь допустимых candidate coordinates. После post-freeze semantic decode пять выбранных coordinates соответствуют

\[
u\partial_xu,\quad v\partial_yu,\quad \rho^{-1}\partial_xp,\quad \nu\partial_{xx}u,\quad \nu\partial_{yy}u
\]

для `u`-канала и аналогичному набору для `v`-канала.

## 2. Numerical differentiation

Производные в primitive-field owner строятся локальным симметричным stencil radius 3. Веса вычисляются из moment conditions, а не задаются под конкретный PDE:

\[
\sum_{j=-3}^{3} w_j j^k = \delta_{km}m!,\qquad k=0,\ldots,6.
\]

Для шага `h` оператор порядка `m` использует `w_j/h^m`. В контрольном эксперименте interior rows исключают boundary points, для которых полный stencil недоступен. Поэтому уровень ошибки уже определяется не аналитической точностью exact term fixture, а погрешностью sampled-field differentiation.

## 3. Primitive-field blind result

Текущий проверенный replay получил в обоих momentum lanes минимальный effective support из пяти axes: одна baseline coordinate была выбрана Atlas discovery-only baseline search, а ещё четыре coordinates активированы одним multi-axis birth.

Для `x`-lane:

\[
\operatorname{NRMSE}_{discovery}\\approx2.61\times10^{-4},\qquad
\operatorname{NRMSE}_{sealed}\\approx3.45\times10^{-4}.
\]

Для `y`-lane:

\[
\operatorname{NRMSE}_{discovery}\\approx3.06\times10^{-4},\qquad
\operatorname{NRMSE}_{sealed}\\approx3.82\times10^{-4}.
\]

После post-freeze decode коэффициенты близки к

\[
(-1,-1,-1,+1,+1),
\]

с отклонениями порядка `10^-4`. Это согласуется с шестым порядком локального finite-difference stencil на текущих сетках и не требует передачи derivative columns в request.

## 4. Что именно квалифицировано и что ещё нет

Primitive-field PASS квалифицирует цепочку

\[
\text{sampled primitive fields}
\to\text{Atlas-born typed local operators}
\to\text{adaptive multi-axis support}
\to\text{sealed OOD transfer}.
\]

Он не квалифицирует полное математическое изобретение произвольной differential grammar. Набор primitive operations пока существует как безопасная domain-neutral grammar внутри Theory Compiler. Следующий уровень должен разрешить Mathematical Invention Kernel рождать новые operation families при residual, если текущие `D`, `D^2`, product и reciprocal-product primitives недостаточны.

## 5. Рождение operator language из translation algebra

Level 3 заменяет заранее заданный differential alphabet более слабой конструкцией. Пусть локальный chart содержит координату `q` и sampled field `f(q)`. Базовым объектом является операция локального сдвига

\[
(\tau_h f)(q)=f(q+h).
\]

Atlas не получает символы `D`, `D^2`, `gradient` или `Laplacian`. Из конечного семейства локальных сдвигов он строит линейные response functionals

\[
L_r[f](q)=\frac{1}{h^r}\sum_{j=-R}^{R}w_j^{(r)}f(q+jh),
\]

где веса определяются dual moment conditions

\[
\sum_{j=-R}^{R}w_j^{(r)}j^k=\delta_{kr}r!,\qquad k=0,\ldots,2R.
\]

Здесь `r` — **rank shell generated by search**, а не переданное имя derivative order. Только после post-freeze decode `r=1` и `r=2` можно интерпретировать как привычные first/second local differential responses.

## 6. Typed composition birth

Для response field `f_a`, coordinate `q_i` и carrier field `f_b` Mathematical Invention генерирует pointwise compositions

\[
L_r[f_a],\qquad f_b L_r[f_a],\qquad f_b^{-1}L_r[f_a],
\]

но retained signature должен иметь dimension frozen target relation. Если target field `f_*` эволюционирует по time-like coordinate `t`, то target relation dimension есть

\[
[T_*]=[f_*]-[t].
\]

Для каждого generated signature проверяется

\[
[L_r[f_a]] + s[f_b] = [T_*],\qquad s\in\{-1,0,+1\}.
\]

Таким образом порядок локального response, выбор response field, carrier и reciprocal/product role возникают из dovetail shells + typing, а не из каталога PDE terms.

Time-like coordinate исключается из predictor signatures и используется только для target response. Это необходимая anti-leakage граница: иначе `L_1[f_*](t)` мог бы тривиально объяснить сам себя.

## 7. Open-endedness и вычислительный бюджет

Scientific rank ceiling отсутствует:

\[
\texttt{FIXED\_GLOBAL\_OPERATOR\_RANK\_CEILING}=\varnothing.
\]

Конкретный запуск имеет finite resource shell budget `B`, но receipt фиксирует возможность продолжения

\[
r>B
\]

в следующем research cycle. Следовательно, `B` — вычислительная остановка, а не утверждение о том, что higher-order operators невозможны.

Аналогично support search использует полный subset enumeration только когда он помещается в trial budget. Иначе применяется sparse forward-backward trajectory без заранее заданного числа axes. Пусть текущий support `S_k`. Forward step выбирает

\[
a^*=\arg\min_{a\notin S_k} E_{holdout}(S_k\cup\{a\}),
\]

после чего, когда frozen fit gate выполнен, backward stage ищет удаляемые axes

\[
a^- = \arg\min_{a\in S_k}\{E_{holdout}(S_k\setminus\{a\}) : E_{holdout}\le \varepsilon_*\}.
\]

Cardinality определяется траекторией evidence, а не параметром `k_target`.

## 8. Level-3 blind result

На controlled continuum world оба momentum lanes породили один и тот же размер operator language: 20 signatures в rank shells `10 + 8 + 2`. Шесть signatures были численно неидентифицируемы на discovery observations и оставлены вне support search; 14 вошли в adaptive search.

Для `u`-lane sparse search выполнил 106 support trials и активировал 4 dormant axes. С baseline effective support содержит 5 axes. Получено

\[
\operatorname{NRMSE}_{disc}=2.6136\times10^{-4},\qquad
\operatorname{NRMSE}_{sealed}=3.4519\times10^{-4}.
\]

Для `v`-lane выполнено 78 support trials, также активированы 4 dormant axes:

\[
\operatorname{NRMSE}_{disc}=3.0600\times10^{-4},\qquad
\operatorname{NRMSE}_{sealed}=3.8246\times10^{-4}.
\]

После post-freeze semantic decode generated ranks `1` и `2` в выбранном support совпадают с локальными first/second differential responses, а найденная структура совпадает с контрольным momentum balance. Rank-3 shell был рожден как допустимый higher-order language shell, но не вошёл в final support.

Именно это является новым квалифицированным свойством Atlas: система не только выбирает закон в fixed differential language, а способна сначала расширить representation language из более слабого translation/algebra substrate и затем найти устойчивый support.

Граница результата остаётся строгой:

\[
\texttt{REPRESENTATION\_ACTIVATED}\neq\texttt{CAUSALLY\_ESTABLISHED},
\]

и

\[
\texttt{PASS\_BLIND\_OPERATOR\_LANGUAGE\_INVENTION}
\not\Rightarrow
\text{new physical law or world mathematical novelty}.
\]

## 9. Residual-driven algebra-depth birth

Level 4 вводит различие между rank shell локального translation response и algebraic carrier depth. Пусть

\[
L_r[f]
\]

— generated local response rank `r`. Вместо только одного pointwise carrier система допускает monomial family

\[
M_{\mathbf s,r}[f]
=
\left(\prod_{j=1}^{m} g_j^{s_j}\right)L_r[f],
\qquad s_j\in\mathbb Z,
\]

с текущей resource complexity

\[
\|\mathbf s\|_1=\sum_j |s_j|.
\]

Начальный search использует `||s||_1 <= 1`. Если frozen discovery residual не проходит fit gate, следующий cycle открывает shell `||s||_1 <= 2`. Никакой конкретный hidden monomial не добавляется вручную: перечисляются composition signatures, разрешённые seed operations `POINTWISE_MULTIPLY`, `POINTWISE_RECIPROCAL` и dimensional typing.

Комбинации с взаимным сокращением powers не являются новыми shells. Например, `g*g^-1` редуцируется к более низкой глубине и отбрасывается до support search.

## 10. Controlled incomplete-theory world

Для квалификации взят masked scalar local evolution world. Его semantic form хранится только в fixture builder и post-freeze verification:

\[
u_t=-a u_x-\lambda c u u_x,
\qquad \lambda=0.65.
\]

Поле `c` безразмерно и независимо меняется между discovery и sealed realizations. Поэтому hidden correction

\[
-\lambda c u u_x
\]

нельзя заменить одним глобальным coefficient при `u u_x`.

Для точного reference solution используется affine family

\[
u(x,t)=\frac{A_0x+B_0-aA_0t}{1+\lambda cA_0t},
\]

для которой непосредственно

\[
\partial_tu=-a\,\partial_xu-\lambda c u\,\partial_xu.
\]

В search input semantic symbols `u,a,c` заменены opaque field ids. Frozen baseline сообщает только одну operator signature, соответствующую известной неполной части; hidden term signature и `lambda` до freeze отсутствуют.

## 11. Level-4 blind result

Carrier depth `1` породил 4 signatures и оставил

\[
\operatorname{NRMSE}_{initial}=5.555687904876772\times10^{-1}.
\]

Это вызвало residual-driven expansion. Carrier depth `2` породил 26 signatures. Adaptive support minimization оставил baseline и одну новую coordinate. После post-freeze decode новая coordinate соответствует two-factor monomial `c*u*L_1[u]`.

Recovered coefficients:

\[
\hat\beta_{base}=-0.9999999999998731,
\qquad
\hat\beta_{hidden}=-0.6499999999999957.
\]

Final errors:

\[
\operatorname{NRMSE}_{disc}=1.5146444163333484\times10^{-13},
\]

\[
\operatorname{NRMSE}_{sealed}=1.5289221198455143\times10^{-13}.
\]

Итог:

\[
\boxed{\texttt{PASS\_BLIND\_HIDDEN\_TERM\_DISCOVERY}:19/19}
\]

Это квалифицирует mechanism

\[
\text{incomplete representation}
\rightarrow\text{persistent residual}
\rightarrow\text{operator-language expansion}
\rightarrow\text{new coordinate birth}
\rightarrow\text{sealed falsification}.
\]

Верхняя квитанция Level 4 дополнительно вводит provenance-связь:

```math
Pi_L4 = Bind(D_input, D_axis, D_H, D_code, D_result, D_receipt).
```

Общий PASS допустим только при полной проверке обязательных полей, валидном digest квитанции и совпадении привязок к коду и результату. Статус `ATLAS_NATIVE_PROVENANCE_ACCEPTED_NOT_SCIENTIFIC_PROMOTION` утверждает происхождение вычисления, но не научную истинность.

Scientific promotion по-прежнему запрещена автоматически:

\[
\texttt{HYPOTHESIS\_SURVIVES\_CURRENT\_HELDOUT\_EVIDENCE\_NOT\_LAW},
\]

\[
\texttt{CAUSALLY\_NOT\_ESTABLISHED}.
\]
