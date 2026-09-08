# ATLAS AI Laboratory Extension 0.6.0

Этот архив предназначен для вложения в другой архив Atlas как отдельное расширение.
Он **не изменяет корневые файлы Atlas автоматически** и не создаёт параллельного scientific owner для уже существующей capability.

## Что содержит

- `ai-model-execution-owner/1.0.0` — единственный authoritative owner исполнения AI factorial experiments;
- 10 algorithm-free capability-contract owners;
- JSON-command backend adapter;
- CLI `scienceatlas-ai-lab`;
- frozen Frontier 003 design: 168 model configurations × 4 regimes = 672 measurement slots;
- fail-closed guards против fixture-as-science, missing budget/evaluator/backend и binary-float scientific scores.

## Вариант A — оставить расширение вложенным

Поместить весь каталог, например:

```text
<ATLAS_ROOT>/extensions/ATLAS_AI_LAB_EXTENSION_v0_6_0/
```

Из корня Atlas предпочтительно установить уже собранный wheel (сеть и build-backend не нужны):

```bash
python -m pip install --no-deps ./extensions/ATLAS_AI_LAB_EXTENSION_v0_6_0/dist/scienceatlas_ai-0.6.0-py3-none-any.whl
```

Исходники также сохранены в `src/` для аудита и разработки.

После установки доступен:

```bash
scienceatlas-ai-lab --help
```

## Вариант B — development/import без установки

```bash
PYTHONPATH=extensions/ATLAS_AI_LAB_EXTENSION_v0_6_0/src python \
  extensions/ATLAS_AI_LAB_EXTENSION_v0_6_0/VERIFY_EXTENSION.py
```

## Реальный backend

Frozen experiment нельзя считать выполненным только от наличия этого расширения. Нужен внешний runner одной model family в трёх scales, который реально управляет `R,V,M,W,E` и возвращает rational score.

Пример вызова:

```bash
scienceatlas-ai-lab \
  --backend-spec frontier003/BACKEND_SPEC.json \
  --manifest frontier003/RUN_MANIFEST.csv \
  --results-template frontier003/RESULTS_TEMPLATE.csv \
  --results-output RESULTS_COMPLETE.csv \
  --receipt AI_LAB_RECEIPT.json \
  --seed 20260906 \
  -- python real_backend_runner.py
```

Scientific run fail-closed, если backend не имеет `real_measurement=true` или не аттестует все обязательные capabilities.

## v0.7.0 integration into ScienceAtlas 15.17

The extension remains subordinate to the canonical Atlas registry. Install the wheel in an isolated environment and mount the Atlas distribution read-only:

```bash
python -m pip install --no-deps dist/scienceatlas_ai-0.7.0-py3-none-any.whl
python VERIFY_EXTENSION.py --atlas-root /path/to/ScienceAtlas
python e2e.py
```

v0.7.0 adds the prospective research loop, operator genesis, regional continual learning, lifetime alpha bookkeeping, composite persistence/rehydration and revocation. Qualified owner↔axis bindings from `data/knowledge/knowledge_evolution_state.json` are read as semantic context only. They never become exact quantity/unit/dimension lowerings and never create a cross-domain bridge.

Synthetic fixture data may verify the loop but may not support a scientific claim. Canonical Atlas mutation remains forbidden from this extension.


## 15.19 host note

`epoch_genesis.py` is additive. Do not replace `research_loop.py`: the 15.18 acquisition boundary supplies the evidence fingerprint required by the scoped ledger. The sequential permutation controller is not anytime-valid; `DEFERRED_RESOURCE` must be handed to a compute scheduler and must not be converted into a scientific rejection.

## v0.9.0 package identity repair for ScienceAtlas 15.19.1

The distributable component identity is now `scienceatlas-ai 0.9.0`. The directory, wheel metadata, runtime package version and integration manifest use the same component version. States emitted by the 0.7.0 runtime remain accepted for migration; new states are emitted as 0.9.0. Install with:

```bash
python -m pip install --no-deps dist/scienceatlas_ai-0.9.0-py3-none-any.whl
```

15.19.1 does not change the accepted autonomous scientific behaviour of 15.19.0. The valid sequential controller still reaches the qualified `DEFERRED_RESOURCE` frontier before exact blind-law recovery; this packaging repair must not be read as a new discovery claim.


## v0.10.0 / ScienceAtlas 15.20.0

Install the current component with:

```text
python -m pip install --no-deps dist/scienceatlas_ai-0.10.0-py3-none-any.whl
```

`PermutationEProcessOwner` is per-target only. Orbit evaluation freezes the Genesis journal and performs no journal writes. A threshold crossing cannot by itself promote an Atlas-wide scientific law; global online e-value control is not yet implemented.
