# NASA Exoplanet 2026 — blind observational experiment

> Происхождение: исследовательский отчёт из `Atlas_Deep_Research_Patch_15_24_0_v1_0_0_FINAL.zip`. Приведённые ниже результаты сообщены автором патча; они не являются новым локальным запуском при интеграции. Исходный NASA-каталог в архив не включён. Этот Markdown хранится как контролируемая документация, отдельно от двух текущих исполняемых релизных receipts.

## Статус

**EXPERIMENT_EXECUTED_NOT_SCIENTIFIC_PROMOTION**

Источник: `PSCompPars_2026.09.20_07.33.39.csv` — 6366 строк × 84 столбцов.
SHA-256 данных: `6129d26e657e1a26256b12fe151886fa28f5530e460578b5d68ab8bda939af9a`.
Freeze digest: `8e197cb6741045e15cef283838545b5054b4a25b501a2ceeaba4d277233ba44e`.

Важно: это PSCompPars, а не PS/default_flag=1. NASA предупреждает, что PSCompPars может объединять значения из разных источников и включать вычисленные значения; поэтому физическая новизна по этому прогону не устанавливается.

## 1. Dimensional positive control

Atlas перебрал 172 безымянных целочисленных структурных кандидатов только на discovery-hosts.
Замороженный победитель: `(3, -2, -1)`, rho=0.028239793.
Порожденная размерность: `(3, -1, -2, 0, 0, 0, 0)` = L^3 M^-1 T^-2.
После freeze эта размерность сопоставилась с `CONST-G` в реестре.
Post-freeze numeric control: G_hat=6.668362037480e-11, G_registry=6.674300000000e-11, относительное расхождение=-0.08897%.

Transfer замороженного кандидата:

- discovery: 3322 planet-rows / 2447 hosts; rank=1; rho=0.028239793; sd(log C)=0.175810.
- validation: 1154 planet-rows / 844 hosts; rank=1; rho=0.025059411; sd(log C)=0.152006.
- sealed: 1117 planet-rows / 836 hosts; rank=1; rho=0.023506640; sd(log C)=0.134428.

## 2. Residual-driven multi-axis birth

Для residual-stage использована одна детерминированно выбранная планета на host, чтобы исключить межпланетную утечку внутри одной звёздной системы.
Полностью наблюдаемые host-системы: 2225; discovery=1327, validation=438, sealed=460.
Начальная модель остатка: intercept-only. Dormant-оси не входили в формулу до residual evidence.

Discovery NRMSE: 1.261340 → 1.256265.
Validation NRMSE: 1.001672 → 1.002343.
Sealed NRMSE: 1.000007 → 0.991291.

Итог этого **первого shell-1 маршрута**: улучшение discovery минимально, validation ухудшился, sealed улучшился менее чем на 1%. Этот 33-trial greedy cycle не установил переносимую residual-закономерность, но он **не являлся сканированием всего residual-пространства**; глубокая коррекция приведена в разделе 8.

Atlas kernel status: `REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES`.
Лучший sparse hypothesis текущего shell: `c0 + c1*eccentricity + c2*discovery_year_centered`.
Параметры: `[-0.05533546861208567, 0.03703181391020741, 0.0025089794658038236]`.

## 3. Что именно Atlas обнаружил

На discovery residual-scan максимальные прямые сигналы получили uncertainty stellar mass, stellar radius, uncertainty semimajor axis, discovery year, stellar log g и eccentricity. Однако эти сигналы не дали устойчивого улучшения на независимой validation выборке.

В исходном прогоне до axis-selection patch kernel формально активировал все 17 dormant-осей, хотя итоговая sparse-гипотеза использовала только `eccentricity` и `discovery_year_centered`. Это было не физическим открытием, а обнаруженным недостатком прежнего axis-activation rule: очень малое discovery-улучшение было достаточно для активации слишком широкого набора осей. Раздел 7 фиксирует устранение этого дефекта.

## 4. Научная граница

- Новый физический закон: **не установлен**.
- Новая причинная ось: **не установлена**.
- Переносимая residual representation в первоначальном shell-1: **не подтверждена validation**; это не означает исчерпания глубоких зон.
- Positive-control dimensional structure: **успешно воспроизведена и перенеслась на host-sealed split**.
- PSCompPars не является self-consistent PS solution table; текущий результат нельзя использовать для утверждения новой физики.

## 5. Аудит реализации

- Intercept-only baseline для frozen residual сохранён без искусственного predictor.
- Общий axis-selection contract модернизирован в существующем `AdaptiveResearchKernel`: marginal gain + group stability + parsimony + final exact-set stability.
- Состояния `representation activated` и `effective formula support` разделены.
- Выявленный интеграционный разрыв public API для существующего closed-loop owner устранён: `run_closed_loop_research` зарегистрирован как mutation surface.
- После финальных правок критический regression-набор adaptive/exoplanet/function-language/query/direct-target/turbulence/closed-loop + ключевые unified checks: **54/54 PASS** после limit/provenance integration.
- Полный `pytest` сейчас собирает **151 tests**, но монолитный запуск и длинные frontier-тесты превышают лимит исполнения текущего контейнера; поэтому полный release-wide PASS не заявляется. Явных failure после исправления трёх найденных интеграционных дефектов в доступных завершённых наборах нет.
- `seal_audit` пока остаётся FAIL, потому что текущая рабочая ветка содержит ранее не включённые в release controls файлы и изменённые controlled files; новый sealed release в рамках этого эксперимента не объявляется.

## 6. Следующий корректный шаг

1. Не использовать уже раскрытый PSCompPars sealed split для нового научного подтверждения.
2. Выполнить тот же frozen selection contract на self-consistent NASA `PS` с `default_flag=1` либо на новом временном snapshot.
3. Validation и sealed должны только проверять уже выбранную representation; они не могут менять axes или stability gate.
4. Только переносимый эффект, переживший новый sealed test, переводить из representation-candidate в дальнейшую физическую проверку.
5. Отдельно, перед выпуском нового дистрибутива, завершить release-wide long tests и затем пересобрать `RELEASE_MANIFEST.json`, `HASHES.txt` и `FILE_TREE.md`; до этого seal не считать закрытым.


## 7. Post-audit qualification: axis-selection contract

После обнаружения массовой активации 17 dormant-осей общий `AdaptiveResearchKernel`
модернизирован replacement-in-place. Новый контракт включает marginal forward gain,
discovery-only group stability, parsimony/backward minimization, final exact-set stability и
раздельные состояния `representation activated` / `effective formula support`.

Повтор на **том же** PSCompPars snapshot выполнялся только как regression и не является новым
blind scientific confirmation. Результат regression:

- representation activated axes: `log_stellar_radius_solar`;
- effective support axes: `log_stellar_radius_solar`;
- activated-but-unused axes: none;
- final stability: PASS, positive fold fraction = 0.75;
- median relative gain = 0.0119286731;
- robust sigma `1.4826*MAD` = 0.0052585871;
- robust margin = 0.0066700860;
- discovery NRMSE: 1.2613404160 → 1.2604446797;
- independent validation NRMSE: 1.0016716183 → 1.0034226783 (worse).

Таким образом, исправлен именно defect широкого activation: 17 → 1 axis на regression fixture,
при этом независимая validation не подтверждает перенос, поэтому scientific promotion остаётся
закрытым. Раскрытый sealed split не используется для выбора или для нового научного утверждения.
Следующая научная проверка требует нового snapshot либо self-consistent NASA `PS` с
`default_flag=1`. Чтобы будущие данные не меняли protocol постфактум, существующий
`evaluation/exoplanet_nasa2026_blind_experiment.py` уже принимает только чистый PS input,
где все конечные `default_flag == 1`; смешанный PS fail-closed. Frozen protocol SHA-256:
`5d10f1fb15f589b3dcf198d93fc27f17a104cc7ebbbf0236a10ec87f6a40a1a7`.

## 8. Deep-zone audit: correction of the shell-1 conclusion

Проверка реализации показала, что прежний NASA residual-run был поверхностным: при 17 dormant
axes он выполнил 17 singleton trials, выбрал одну ветвь и проверил только 16 добавлений к ней —
всего **33 trials** при `complexity_level=1`. Пары/тройки, которые работают только совместно,
не исследовались. Поэтому формулировка «residual space практически исчерпан» снята как
необоснованная.

Existing `AdaptiveResearchKernel` модернизирован replacement-in-place, без нового owner:

- multi-start joint-zone reconnaissance допускает совместное рождение осей без stable singleton parent;
- перспективные pair zones выборочно углубляются в следующий cardinality shell;
- activated joint zone обязана иметь full effective support;
- selection между зонами использует repeated discovery-only group partitions, а не одну разбивку;
- composite terms выбранной гипотезы сохраняются как `RESEARCH_LOCAL_DERIVED_AXIS_CANDIDATE` в `next_state`, canonical registry не мутируется;
- trial budget остаётся execution tranche, а не доказательством исчерпания пространства.

Независимый synthetic control `y=z*w` сначала доказал общий механизм: старый greedy route
пропускал pure synergy; новый route рождает `{z,w}` совместно и материализует derived axis
`z*w` без подсказки физического смысла.

На том же уже раскрытом PSCompPars затем выполнен **exploratory** deep-zone run:
`complexity_level=2`, 256 trials. Он действительно нашёл зоны, которые 33-trial route не
посещал. Одна из них `(log_planet_mass_earth, log_stellar_radius_solar, log_distance_pc)`
давала single-partition discovery stability и после freeze улучшала validation
`1.0016716 -> 0.9982421` (~0.342%). Однако repeated discovery partitions показали, что эта
зона partition-fragile, поэтому она не может считаться устойчивой representation.

После repeated-stability selection текущая discovery-only ветвь выбрала
`(log_stellar_radius_solar, stellar_logg_cgs)` с composite term
`log_stellar_radius_solar*stellar_logg_cgs`. Ее five-repeat stability receipt:

- repeat pass fraction = 0.60;
- median repeat robust margin = 0.0060033;
- pooled robust margin = 0.0004657;
- discovery holdout NRMSE = `1.2613404 -> 1.2603280`.

Только после выбора была прочитана validation: `1.0016716 -> 1.0042192`, то есть перенос не
подтвердился. Поэтому deep scan **не установил новый закон**, хотя он доказал наличие ранее
непосещённых interaction zones и необходимость дальнейшего representation growth.

Residual-driven `FunctionLanguageBirthEngine` на discovery-only residual additionally emitted
`LATENT` (signal 0.2269) and `EXPONENTIAL` (0.1405) operation signatures. Это направления
следующего selective shell, а не научные утверждения. Старый sealed split уже раскрыт и не
может использоваться для подтверждения этих candidates; нужна новая self-consistent
`PS/default_flag=1` выборка или новый temporal sealed snapshot.

Связанная регрессия после deep-zone/derived-axis patch: adaptive 14/14, exoplanet 10/10,
closed-loop 10/10, function-language 8/8, query-driven 4/4, direct-target 1/1,
turbulence 4/4 — суммарно **51/51 PASS** в этих целевых контурах.

Report digest: `4fec6bd9fcf2b32b327abc490dc651772aa5808388e1f5b3026a287a1e7f36b0`.

## Selective language shell — LATENT + EXPONENTIAL (exploratory continuation)

The earlier deep-zone receipt was used as research state, including the non-canonical born coordinate
`DERIVED-F2CDF242DEE9DAE3B96A = log_stellar_radius_solar * stellar_logg_cgs`.
The next discovery-only language tranche examined 207 stage-1 single/pair specifications and 246 selective
stage-2 deepened specifications, with repeated host-group refits. This is a finite compute tranche, not an
exhaustive scan.

After refitting the previous deep model, current residual diagnosis still births `LATENT` (signal 0.230717),
while `EXPONENTIAL` falls below the current 0.12 birth gate (0.111972). EXPONENTIAL was nevertheless retained
as a persisted exploratory branch because it had been born in the previous shell.

The strongest persisted EXPONENTIAL branch uses `(log_stellar_radius_solar, stellar_logg_cgs)`, scale 0.5.
It is very stable inside discovery (5/5 repeat pass; pooled median gain 0.04630) but fails outer transfer:
`NRMSE 1.002209 -> 1.053033` (-5.071% relative gain). It is rejected as a transferable representation.

The current-residual-supported LATENT branch uses
`(DERIVED-F2CDF242DEE9DAE3B96A, log_planet_mass_earth, log_planet_radius_earth)` with one latent component and
a degree-2 latent polynomial. Discovery repeated stability passes 5/5; pooled median relative gain is 0.006515
and pooled robust margin 0.002079. Its born coordinate is approximately

`L = -0.446144 z(D) -0.632923 z(log Mp) -0.632743 z(log Rp)`.

On the already-disclosed outer validation it gives `NRMSE 1.002209 -> 0.997443`, an exploratory +0.4756%
relative improvement. Because this validation is not fresh blind evidence, the candidate is retained only as a
research-local representation. No new physical law, causal axis, or canonical axis is claimed.

## Post-LATENT continuation shell — LATENT + KERNEL

Этот цикл продолжает предыдущий selective-language state и **не начинает поиск заново**. Замороженная research-local ось
`LATENT-FE1E032E32E1DC03E9A8` используется как полноценная координата `L`; её веса и стандартизация не меняются.
Внутри каждого discovery fold переоцениваются только коэффициенты уже выбранной deep+LATENT correction, после чего новый
language candidate обучается на остатке. Validation и sealed не участвуют в выборе.

После вычитания frozen deep+LATENT stack discovery residual снова потребовал расширения языка:

- `LATENT`: signal = `0.232729`;
- `KERNEL`: signal = `0.123338`;
- `EXPONENTIAL`: `0.117986`, то есть ниже birth gate `0.12`.

Таким образом residual не возвращается к прежнему EXPONENTIAL-направлению; вместо него Atlas рождает KERNEL branch.
В persistent coordinate space сохранены исходные 17 observable axes, composite axis
`DERIVED-F2CDF242DEE9DAE3B96A`, frozen LATENT axis `L` и ранее родившиеся EXP axes. Они доступны для selective navigation,
но их наличие не означает поддержку текущим residual.

Интегрированный tranche выполнил 246 reconnaissance specifications и 83 selectively-deepened specifications.
Stage 1 является дешёвым discovery reconnaissance; только surviving branches получают 5 independent deterministic
host-group partitions на stage 2. Compute budget снова является execution tranche, а не scientific-space ceiling.

Discovery-only winner: `LATENT` на зоне
`(EXP-57BCA3C83A534E6D3B0A, EXP-D6D01283E6581A265C43, log_stellar_radius_solar)`,
с `components=2`, `degree=2`. Repeated stability: pass fraction `0.60`, pooled median gain `0.0275783`,
pooled robust margin `0.0019768`, pooled positive fraction `0.90`.

До нового языка предыдущий deep+L stack имеет discovery NRMSE `0.9901309`; после выбранной LATENT representation:
`0.9572124`. Однако outer validation после freeze ухудшается:

`0.9974428 -> 1.0213037`, relative gain `-2.3922%`.

Следовательно, эта новая LATENT representation **не переносится** и не получает scientific promotion.
Она рождает две новые non-canonical research-local latent coordinates:
`LATENT-184E1C2B8640AD2B3DF8` и `LATENT-7366B56534D976B6082D`.

KERNEL branch действительно был рождён residual, но его лучший selectively-deepened кандидат не прошёл final repeated-stability:
repeat pass fraction `0.40`, pooled median gain `0.0035369`, pooled robust margin `-0.0063220`.
Поэтому KERNEL representation не материализуется как promoted/effective branch в этом цикле.

После вычитания discovery-selected representation residual всё ещё рождает `LATENT` (`0.243003`) и `KERNEL` (`0.140678`).
Это означает, что representation gap сохраняется и пространство не исчерпано. Однако уже раскрытая outer validation не может
использоваться для настройки следующего shell или для научного подтверждения. Sealed split в этом continuation не читался.

Статус цикла: `EXPLORATORY_REPRESENTATION_GROWTH_CONTINUES_NO_TRANSFER_CONFIRMED`.
Связанная regression-квалификация после интеграции continuation mode: adaptive+exoplanet+function-language `32/32 PASS`,
query-driven+closed-loop+direct-target+turbulence `19/19 PASS`, итого **51/51 PASS** в затронутых контурах.


## Final multibranch closure — group stability + tail stress

После сохранения конкурирующих ветвей `D`, старого `L`, `L1/L2`, EXP-derived axes и KERNEL frontier выполнен единый discovery-only multibranch tranche.

- Wide reconnaissance: **311** branch-zones.
- Discovery evidence: LATENT `0.02876817`, KERNEL `0.00366910`.
- Expensive repeated-CV budget: **34 LATENT + 14 KERNEL = 48** кандидатов.
- Каждый deep candidate проверялся на 5 deterministic host-group partitions.
- Validation не использовалась для выбора; sealed не читался.

Лучший pre-stress discovery branch:

`LATENT(EXP-5E5AA1EADD8BD044C041, stellar_logg_cgs)`,
где `EXP-5E5... = exp(+0.5 * standardize(log_stellar_radius_solar))`.

Repeated group metrics:

- repeat pass fraction: `0.8`;
- pooled median gain: `0.03375588`;
- pooled robust margin: `0.00576511`;
- pooled positive fraction: `0.95`;
- discovery NRMSE: `0.99013094 -> 0.95044781` (`+4.0079%`).

Но discovery-only 15% lower/upper tail stress дал:

- median tail gain: `-3.21027929`;
- robust margin `median - 1.4826*MAD`: `-7.91014544`;
- positive tail fraction: `0.0`;
- tail gate: **FAIL**.

Outer validation была прочитана только после discovery selection и подтверждает нестабильность, но не используется как причина выбора/отказа:

`0.99744277 -> 1.35256600`, relative gain `-35.6034%`.

Итог frontier:

`joint_pass_count = 0`.

Финальный статус текущего цикла:

`REPRESENTATION_GAP_FRONTIER_OPEN_NO_STRESS_ROBUST_BRANCH`.

Дополнительная stress-проверка старого LATENT-axis `L`, который ранее показывал небольшой положительный outer transfer, также не прошла robust tail gate: median `0.001307`, positive fraction `0.625`, robust margin `-0.025784`.

Следовательно, прежнюю формулировку о «surviving LATENT representation» следует читать только как историю exploratory search. После введения regime stress ни один residual-born объект не имеет достаточного evidence для scientific promotion.

Научно устойчивым результатом остаётся positive control `a^3/(P^2 M_star)` с rank 1 на всех исходных splits и post-freeze `G_hat = 6.668362037e-11`, relative difference около `-0.089%`. Всё последующее является структурированным, но не stress-robust residual frontier.

## Availability-adaptive full-catalogue pass — 6366/6366 passports

Все 6366 input rows сохранены как observational passports. После provenance audit non-zero NASA `*lim` fields больше не трактуются как центральные физические значения: `LIMIT != CENTRAL VALUE`.

Исправленное покрытие:

- observed central `(P,a,M_star)`: **5589**;
- model-assisted orbital: **761**;
- orbital-calculable: **6350**;
- orbital unresolved: **16**;
- central mass+radius planet structure: **6098**;
- stellar structure: **6033**;
- irradiation checks: **5609**;
- eccentric geometry: **4933**;
- full 17-axis central observed-orbit subset: **2467**.

В snapshot содержатся 234 planet-mass limits и 5 planet-radius limits. Они остаются censored evidence и не участвуют как point values в density/two-body/residual calculations.

### Исправленный selection effect

Complete-case median absolute orbital residual: `0.0092285`; non-complete central observed population: `0.0269890`; отношение **2.9245×**. Прежнее `4.14×` заменено: оно было завышено из-за limit-semantics bug. Population-wide maximal-availability scan по-прежнему даёт **0/17** устойчивых singleton orbital residual axes.

### Provenance audit 13 density flags

Legacy naïve calculation воспроизводит ровно 13 прежних flags. После limit/uncertainty audit:

- 11/13 = `INPUT_LIMIT_NOT_PHYSICAL_POINT` (`pl_bmasselim != 0`);
- `KOI-2513.01` и `Kepler-37 e` = `UNCERTAINTY_UNRESOLVED`;
- **0/13** остаются stress-robust physical high-density anomalies.

### Provenance/regime audit 363 irradiation flags

Все 363 классифицированы по joint `S`/`Teq` consistency:

- 312 `COMPOSITE_INSOLATION_ONLY_MISMATCH`;
- 22 `COHERENT_LITERATURE_A03_LIKE`;
- 18 `COHERENT_SOURCE_SCALE_ZERO_ALBEDO_LIKE`;
- 1 `MULTISTAR_OR_PROVENANCE_UNRESOLVED`;
- 10 `OTHER_PROVENANCE_OR_CONVENTION`.

56 candidate rows in 25 multi-planet hosts share near-identical discrepancy factors (≤10% spread), supporting host/source-level provenance rather than planet-specific law.

A cleaned non-extreme insolation residual scan leaves two very weak discovery-only singleton candidates (`log_planet_radius`, `discovery_year`), but both worsen outer validation. Therefore **0 cleaned singleton branches transfer**.


### PS/public-solution spot checks remaining irradiation frontier

Public NASA PS overview records independently support the catalogue/provenance interpretation for several of the final 11 unresolved rows:

- `DMPP-2 b`: published equilibrium temperature explicitly assumes Bond albedo 0.5; this explains why a zero-albedo proxy is not the correct convention for that row.
- `K2-11 b`: published solutions disagree strongly in stellar/planet parameters; the composite row combines a 5.15 R_sun stellar radius with an insolation value traceable to a solution whose host is ~0.83 R_sun, a direct source-mixing signature.
- `K2-22 b`: NASA records stellar multiplicity; a single-star irradiation proxy is not an adequate regime model.
- `Kepler-1624 b`: NASA PS exposes multiple published insolation solutions spanning approximately 6 to 44 S_Earth, directly demonstrating solution/provenance heterogeneity.

These spot checks reduce confidence that the remaining frontier is new planet physics. They do not replace a bulk self-consistent `PS/default_flag=1` replay, which remains the required fresh confirmation surface.

### Corrected known two-body control

After removing censored planet masses, two-body calculation uses 5344 rows. For 112 central systems with `q>0.01`, median absolute log-G residual improves `0.0161666 -> 0.0081193` (~49.8%). This remains known Newtonian two-body physics, not a new Atlas law.

### Final audit status

`13 density flags -> 0 robust physical anomalies`.

`363 irradiation flags -> 352 classified provenance/regime cases + 11 unresolved provenance-frontier cases`.

No new transferable physical residual law survives the cleaned-class rerun. The important new result is methodological and catalogue-specific: censored values, completeness selection and composite-source heterogeneity can create apparently deep residual structure unless provenance semantics are first-class Atlas state.

Frozen NASA runner remains unchanged at SHA-256 `5d10f1fb15f589b3dcf198d93fc27f17a104cc7ebbbf0236a10ec87f6a40a1a7`.



## ATTACK + DEFENSE reinterpretation — candidates are not only falsified

The earlier wording `13 density flags -> 0 robust physical anomalies` was too one-sided. It remains true that none of the 13 is *required* to be an extreme-density object by current constraints, but this does not mean the candidate region is excluded.

After propagating censoring/uncertainty constraints, all 13 legacy density candidates are classified as `EXTREME_ALLOWED_BY_CONSTRAINTS`; `EXTREME_REQUIRED_BY_CONSTRAINTS=0`, `EXTREME_EXCLUDED_BY_CONSTRAINTS=0`. Thus the correct status is **allowed but not forced**, not “destroyed”. Upper limits and `M sini` are retained as inequality evidence.

The 363 irradiation candidates are likewise defended, not only audited. Current defense accounting gives:

- 43/363 directly compatible after observational interval propagation;
- 359/363 thermally compatible with a broad physically admissible albedo/redistribution envelope;
- 56 rows / 25 multi-planet hosts support a coherent `HOST_LATENT_SCALE` candidate, with 5 rows also thermally coherent at the host-scale level.

A cleaned global singleton search still yields no population-wide transferable axis, but predeclared observational-regime defense changes the result. In the `Transit` regime:

- `log_planet_radius_earth` is `DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL`: discovery robust margin `0.0014373`, tail robust margin `0.0169763`, outer-validation gain `+0.0009184`;
- `log_planet_mass_earth` is `DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL`: discovery robust margin `0.0003420`, tail robust margin `0.0171855`, outer-validation gain `+0.0016004`;
- `log_distance_pc` has positive outer transfer but fails tail stress and is retained as `DEFENDED_REGIME_LOCAL_TRANSFER_TAIL_LIMITED` rather than discarded.

These are small research-local signals, not causal or new-physics claims. The important methodological correction is that Atlas now has symmetric candidate semantics:

`ATTACK(candidate)` tries to falsify; `DEFENSE(candidate)` profiles declared uncertainty/censoring/nuisance/validity domains without held-out refit. Global failure may lower a candidate to a regime-local or tail-limited state instead of erasing it.

Therefore the current catalogue result is: **no universal new law is established, but several candidate regions remain observationally allowed, a coherent host-latent scale frontier exists, and two weak Transit-regime axes survive the complete attack+defense stack.**


### Scope defense of the surviving Transit candidates

The two defended Transit associations were additionally challenged/defended with a within-host fixed-effect audit rather than being interpreted immediately as planet-local physics.

- `log_planet_radius_earth`: discovery within-host gain `+0.0043105`, validation within-host gain `-0.0086883` (916 discovery rows / 360 hosts; 365 validation rows / 143 hosts).
- `log_planet_mass_earth`: discovery within-host gain `+0.0036532`, validation within-host gain `-0.0035451` (822 discovery rows / 334 hosts; 338 validation rows / 135 hosts).

Thus both remain real `DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL` **associations**, but their current mechanism scope is `HOST_OR_SURVEY_MEDIATED_CANDIDATE`, not a defended planet-local law. This is a scope refinement, not candidate deletion.

The independent host-latent-scale frontier is unusually coherent: across the 56 flagged rows in 25 multi-planet systems, the median within-host coefficient of variation of `S_catalog/S_model` is `0.0009320` (~0.0932%). This strengthens `HOST_LATENT_SCALE` as a research-local coordinate while leaving its physical/provenance interpretation open.


## Formal hierarchical theory compiled from the 6366-object observational state

Atlas now compiles the exoplanet result into a four-layer theory rather than a flat residual claim:

\[
\log(S_{catalog}/S_{phys})=\alpha_h+f_{\mathcal R}(x_p)+\epsilon.
\]

`alpha_h` is the shared host latent scale, `f_R` is a regime-local planet term and all measured coordinates are constrained by per-object feasible domains `Omega`.

The strongest new result is predictive. On 206 independent validation hosts / 515 held-out planet predictions, estimating `alpha_h` from the other planets of the same system reduces MAE `0.141159 -> 0.052581` (62.75%) and RMSE `0.276852 -> 0.189567` (31.53%). The held-out target planet is never used to estimate its own host scale.

Across 966 multi-planet hosts, 80.54% have max/min `S_catalog/S_model` within 10%; median max/min is `1.00722`. In 64 deterministic null permutations the mean corresponding fraction is 25.01% and the maximum is 27.85%, so the observed same-host coherence exceeds every null permutation.

After interval/censoring propagation, 922/966 (95.45%) multi-planet hosts admit a non-empty common `alpha_h` feasible domain. All 25 previously identified high-coherence host-latent candidates remain feasible (25/25).

Atlas then ATTACKED the host latent coordinate with the tested known host axes (`M*`, `R*`, `Teff`, `logg`, metallicity, distance, discovery year, star count, planet count). No single axis survived the full discovery-stability/transfer logic. A discovery-selected multivariate ridge model also failed (`discovery robust margin=-0.01038`; validation NRMSE `1.02084 -> 1.02917`). Therefore the current status is `HOST_LATENT_SCALE_NOT_EXPLAINED_BY_TESTED_KNOWN_HOST_AXES`, not a new-physics claim.

The previously defended Transit `M_p` and `R_p` associations do not survive within-host outer transfer, so the planet layer remains open and is currently scoped as `HOST_OR_SURVEY_MEDIATED_CANDIDATE` rather than planet-local law.

Formal compiled status:

`PREDICTIVE_HOST_LAYER_SUPPORTED_MECHANISM_UNRESOLVED` (historical pre-refinement status; superseded below by the effective-luminosity representation identification).

Fresh self-consistent `PS/default_flag=1` is still required to decide whether `alpha_h` is catalogue/provenance state, a known but currently unrepresented host variable, or a genuinely missing physical coordinate.

## Host-layer mechanism refinement: effective stellar luminosity representation

The previously predictive `alpha_h=log(lambda_h)` host coordinate has now been algebraically resolved at the representation level.

Define

`L_eff/L_sun = pl_insol * pl_orbsmax^2`

and

`L_RT/L_sun = st_rad^2 * (st_teff/5772)^4`.

Then `lambda_hp = L_eff/L_RT` identically; the maximum observed absolute log-identity error on the current snapshot is `4.44e-16`.

Across 966 multi-planet hosts, median within-host CV of `L_eff` is `0.002887`; 70.29% of hosts are coherent within 1%, 86.34% within 5%, and 90.58% within 10%.

A target-held-out sibling test estimates `L_eff` from the other planets of the host and predicts `S_catalog=L_eff/a^2`. On 206 validation hosts / 515 held-out planets, MAE improves `0.141163 -> 0.042205` (70.10%) and RMSE improves `0.276852 -> 0.185858` (32.87%); 82.52% of targets have lower absolute error than the radius-temperature luminosity baseline.

Thus the earlier status `PREDICTIVE_HOST_LAYER_SUPPORTED_MECHANISM_UNRESOLVED` is refined to

`PREDICTIVE_HOST_EFFECTIVE_LUMINOSITY_REPRESENTATION_SUPPORTED_ORIGIN_UNRESOLVED`.

This does **not** identify the causal origin. The remaining hypotheses are: a published/archive stellar-luminosity source different from the composite `R_star,T_eff` source; a different stellar state/model; host-level provenance/calibration; or, only if the gap persists on fresh self-consistent PS solutions, a missing stellar-physics coordinate.

## P3 — Theory → Experiment Design → Theory Revision

Hierarchical observational theory now carries frozen explanation-specific experimental models. The current exoplanet theory has three live explanations for the host effective-luminosity representation gap: mixed/composite provenance, missing host physics, and planet-local regime structure.

Without inspecting any future measurement, the P3 observational experiment owner selected:

- `experiment_id`: `E-SELF-CONSISTENT-PS-RETEST`
- observable: `FRESH_SELF_CONSISTENT_PS_HOST_GAP_STATE`
- selection rule: maximize minimum pairwise explanation divergence, then mean divergence per cost
- cost: 1.0
- frozen utility: 1.25

The experiment asks whether the host-level luminosity gap collapses, persists, or collapses while a planet-local residual survives when the same systems are re-evaluated on fresh self-consistent `PS/default_flag=1` solutions. The outcome has not been observed in this P3 run. Therefore no explanation is promoted or demoted yet. The experiment is a prospective discriminating test, not evidence.

The generic closed-loop mechanism was separately qualified on a hidden synthetic world: experiment selection happened before the hidden measurement, the maximally discriminating experiment was selected, and the post-freeze measurement correctly identified the hidden explanation without refit.

## P3 — Frozen representational-novelty benchmark

The frozen benchmark passed 10/10 checks. Atlas independently birthed `z*w` on a pure joint-interaction task and both `z*w` and `u*v` on a double-interaction task, transferred the representations to sealed rows at machine-level error, and produced zero false births on an intercept-closed null control. A raw-linear no-birth baseline failed the interaction tasks; a fixed quadratic oracle succeeded only because the interaction grammar was supplied in advance. The benchmark is an internal mechanism qualification and does not establish external scientific priority.
