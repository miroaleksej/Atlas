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
- После финальных правок критический regression-набор adaptive/exoplanet/function-language/query/direct-target/turbulence/closed-loop + ключевые unified checks: **53/53 PASS**.
- Полный `pytest` собирает **147 tests**, но монолитный запуск и длинные frontier-тесты превышают лимит исполнения текущего контейнера; поэтому полный release-wide PASS не заявляется. Явных failure после исправления трёх найденных интеграционных дефектов в доступных завершённых наборах нет.
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
