# Аудит роли тестов Atlas

Тесты Atlas не должны пониматься как проверка ради проверки. В текущей системе они
играют роль исполняемой научной памяти: фиксируют не только корректность функций,
но и границы допустимых утверждений, жизненные циклы гипотез, запреты продвижения
и маршруты от осей к измерениям.

## Что именно защищают тесты

### 1. Доказательные барьеры и запреты продвижения

Эта группа проверяет, что Atlas не превращает гипотезу в закон без полного набора
доказательств, не обходит U5/U6, не смешивает песочницу с научным продвижением и
не меняет канонический реестр без явной авторизации.

Критические файлы:

- `tests/test_unified_current.py`
- `tests/test_promotion_confirmation.py`
- `tests/test_canonical_law_transaction.py`
- `tests/test_scientific_exploitation_current.py`
- `tests/test_research_acceleration_policy.py`
- `tests/test_research_triage.py`

Это не исторический хвост. Это защита от ложного научного заявления.

### 2. Жизненный цикл исследования

Эта группа проверяет переходы:

```text
оси → кандидат → прогноз → эксперимент → измерение → проверка → пересмотр
```

Критические файлы:

- `tests/test_adaptive_axis_discovery.py`
- `tests/test_hypothesis_family_lineage.py`
- `tests/test_closed_loop_research.py`
- `tests/test_discriminating_experiment_autopilot.py`
- `tests/test_u5_attempt_scheduler.py`
- `tests/test_research_acceleration_end_to_end.py`

Эти тесты проверяют не одну функцию, а научный маршрут Atlas.

### 3. Язык представлений и рождение координат

Эта группа проверяет способность Atlas не просто подгонять формулу, а менять язык
представления, когда текущая грамматика не объясняет устойчивый residual.

Критические файлы:

- `tests/test_function_language_birth.py`
- `tests/test_autonomous_representation_language_birth.py`
- `tests/test_meta_language_ontology_birth.py`
- `tests/test_abs_power_parameterized_birth.py`
- `tests/test_query_driven_research_current.py`
- `tests/test_direct_target_residual_discovery.py`

Сюда относится и смысл `source.lawspace.pi_genesis_bridge`: это мост между
найденной безразмерной координатой и проверкой того, хватает ли текущего языка
Genesis для переносимой функции.

### 4. Источники, измерения и fail-closed поведение

Эта группа проверяет, что provider match не считается внешним доказательством,
fresh/sealed данные не используются до freeze, а отсутствие независимого attestor
останавливает изменение world model.

Критические файлы:

- `tests/test_source_capability_observational_archive.py`
- `tests/test_universal_experiment_execution.py`
- `tests/test_jhtdb_freeze_integrity.py`
- `tests/test_fetch_jhtdb_real_snapshots.py`
- `tests/test_jhtdb_observational_adapter.py`
- `tests/test_observational_round_integrity.py`
- `tests/test_world_expansion_domain_consolidation.py`

JHTDB-тесты выглядят предметными, но сейчас они выполняют роль первого regression
case для универсального observational archive / freeze / evidence route. Их можно
будет упрощать только после того, как тот же инвариант будет покрыт общим
контрактным тестом без JHTDB-специфики.

### 5. Доменные qualification cases

Эта группа нужна не для “украшения” репозитория, а чтобы широкий Atlas не
превратился в абстрактный router без проверок на реальных предметных формах.

Примеры:

- `tests/test_exoplanet_dimensional_closure_example.py`
- `tests/test_exoplanet_observations_2026.py`
- `tests/test_turbulence_dns_closure_experiment.py`
- `tests/test_eda_chip_design.py`
- `tests/test_tensor_axisymmetric_current.py`
- `tests/test_curvature_memory_current.py`
- `tests/test_electronic_state_space_current.py`
- `tests/test_universal_scientific_portfolio.py`

Эти тесты не доказывают новые законы. Они проверяют, что общие механизмы Atlas не
ломаются при переносе между предметными областями.

### 6. Seal, digest и воспроизводимость выпуска

Эта группа защищает контентно-адресуемую природу Atlas: изменение исходного
артефакта должно менять квитанцию, а read-only replay не должен загрязнять выпуск.

Связанные маршруты:

- `make release-controls`
- `make seal-audit`
- `make audit-read-only`
- `evaluation/build_release_controls.py`
- `evaluation/seal_audit.py`
- `evaluation/read_only_audit.py`

Эти проверки нельзя удалять как “служебные”: они отделяют воспроизводимый выпуск
от набора скриптов.

## Какие тесты могут считаться кандидатами на упрощение

Тест можно удалить или слить с другим только если выполнены все условия:

1. новый общий route/contract тест покрывает тот же научный инвариант;
2. покрыт отрицательный сценарий fail-closed;
3. покрыта digest/provenance-связка, если тест работал с артефактами;
4. удаление не ослабляет границу `REPRESENTATION_ACTIVATED != CAUSALLY_ESTABLISHED`;
5. после удаления проходят `pytest`, `seal-audit` и `audit-read-only`.

До появления такой замены исторический тест может выглядеть грубо, но всё ещё
быть защитным барьером.

## Вывод

Количество тестов стало большим, потому что Atlas проверяет не только код, а
несколько уровней научной ответственности:

```text
Discovery/Search Core
→ Representation / Language Birth
→ Experiment / Evidence Runtime
→ World Trust / Attestation
→ Promotion / Canonical Registry
→ Release Seal / Reproducibility
```

Профессиональное упрощение должно идти не через массовое удаление тестов, а через
склейку их инвариантов в общий research-route graph. После этого предметные и
исторические тесты можно будет сокращать без потери защитных барьеров.
