# Atlas MCP Gateway — интеграция Φ-Compiler / ScienceAtlas с ChatGPT и Codex

## 1. Назначение

`interfaces/atlas_mcp_gateway.py` — тонкий интерфейс Model Context Protocol (MCP) поверх существующего Atlas. Он **не содержит научных алгоритмов** и не создаёт второй research solver.

Архитектурная граница:

```text
ChatGPT / Codex / MCP client
        |
        v
Atlas MCP Gateway
        |
        v
LawSpaceAPI
        |
        v
ScientificResearchCycleOwner
        |
        +--> AdaptiveResearchKernelOwner
        +--> ResidentCognitiveOrganism
        +--> MathematicalInventionKernel
        +--> existing scientific owners
```

Все механизмы representation birth, adaptive axis birth, hypothesis competition, экспериментального проектирования, scientific promotion и world/resident state остаются владельцами существующего ядра Atlas.

## 2. Что включено в чистый дистрибутив

В ZIP нет `.venv`, установленного `site-packages`, `.git`, Python cache, `.DS_Store`, `__MACOSX` и сгенерированного installation metadata `*.egg-info`.

Сторонние Python-библиотеки **не упакованы**. Они устанавливаются отдельно в окружение исполнения.

Первичный `scienceatlas_ai` wheel и его `build/lib` сохранены, потому что это собственный first-party компонент Atlas, привязанный к текущему `RELEASE_MANIFEST.json`; удаление этих файлов нарушило бы существующую проверяемую границу системы.

## 3. Установка окружения

Минимально:

```bash
python -m venv .venv
source .venv/bin/activate            # Linux/macOS
# .venv\Scripts\activate             # Windows

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -e ".[mcp]"
# эквивалентно для одного SDK: python -m pip install "mcp>=2,<3"
```

`mcp` — официальный Python SDK Model Context Protocol. В `pyproject.toml` он закреплён как optional dependency `mcp>=2,<3`; сам SDK намеренно не включён в архив.

## 4. Локальная проверка Atlas без MCP SDK

Сам gateway импортирует MCP лениво. Поэтому ядро и bridge можно проверять без установленного SDK:

```bash
python -B - <<'PY'
from interfaces.atlas_mcp_gateway import AtlasMCPBridge

bridge = AtlasMCPBridge()
print(bridge.system_status())
print(bridge.search_knowledge("temperature energy", limit=5))
print(bridge.research(
    "исследовать неизвестную зависимость температуры и энергии",
    detail_level="summary",
))
PY
```

`atlas_research` запускает настоящий `LawSpaceAPI.run_autonomous_research()`, а не отдельную имитацию.

## 5. MCP tools

Gateway публикует только четыре целевых инструмента.

### `atlas_system_status`

Read-only. Возвращает состояние релиза, integration layer и authoritative research kernel.

### `atlas_search_knowledge`

Read-only. Ищет существующие scientific entities Atlas через текущий `LawSpaceAPI.search_entities()`.

### `atlas_research`

Read-only относительно Resident state. Вызывает:

```text
LawSpaceAPI.run_autonomous_research(
    commit_resident_state=False
)
```

Это основной инструмент исследования.

### Универсальная formal-verification ветка внутри тех же tools

`atlas_research` и `atlas_research_and_learn` не получили отдельных математических tools. Вместо этого те же четыре внешних инструмента принимают необязательные поля:

```text
proof_artifact
formal_kernel_target = LEAN | COQ | ISABELLE
formal_kernel_attestation
counterexample_search_specs
```

Если `proof_artifact` передан, authoritative `AdaptiveResearchKernelOwner` внутри Atlas выполняет общую цепочку:

```text
FROZEN CLAIM
  -> DEPENDENCY DAG
  -> LEMMA GATES
  -> COUNTEREXAMPLE REGIONS
  -> PROOF OBLIGATIONS
  -> FORMAL KERNEL HANDOFF
```

Эта ветка не привязана к Navier–Stokes или конкретной математической области. Dependency graph сам по себе не считается доказательством; непроверенная лемма остаётся proof obligation; отсутствие контрпримера в конечном неисчерпывающем поиске не доказывает бесконечное утверждение; успешный handoff не считается kernel verification без фактического запуска соответствующего proof kernel.

Подтверждённые **механизмы проверки**, но не истинность отдельных теорем, хранятся в общей `UNIVERSAL-PROOF-MECHANISM-MEMORY/1.0.0` и доступны всем domain plugins через единый Atlas core.

`formal_kernel_attestation` предназначен для внешнего replay receipt. Gateway не трактует его как локальный proof. Core проверяет pinned source/toolchain, theorem outcomes, axiom surface, replay digests и provenance; положительный результат имеет статус `EXTERNAL_FORMAL_ATTESTATION_ACCEPTED` при `locally_kernel_verified=false`. Тем самым ChatGPT/OpenAI может передать Atlas внешний формальный evidence, но не может присвоить ему локальную proof authority.

### `atlas_research_and_learn`

Тот же authoritative research owner, но с:

```text
commit_resident_state=True
```

Resident state сохраняется существующим ядром **вне sealed runtime tree**. Gateway не имеет отдельной памяти и не пишет scientific truth.

## 6. Почему tools не дробятся по внутренним owners

MCP surface намеренно не повторяет сотни методов `LawSpaceAPI`.

Неверная схема:

```text
ChatGPT -> birth_axis()
        -> invent_representation()
        -> choose_hypothesis()
        -> promote_law()
```

Она сделала бы внешнюю модель главным научным orchestrator.

Текущая схема:

```text
ChatGPT -> atlas_research(...)
              |
              v
     ScientificResearchCycleOwner
              |
              v
        existing Atlas
```

Снаружи передаётся исследовательская цель. Внутреннее решение о маршруте остаётся Atlas.

## 7. Запуск MCP

### stdio

```bash
python interfaces/atlas_mcp_gateway.py --transport stdio
```

Подходит для MCP host, который сам запускает локальный процесс.

### Streamable HTTP

```bash
python interfaces/atlas_mcp_gateway.py \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8000 \
  --path /mcp
```

Endpoint:

```text
http://127.0.0.1:8000/mcp
```

Gateway v1.3.0 по умолчанию разрешает Streamable HTTP только на loopback (`127.0.0.1`, `localhost`, `::1`). Non-loopback bind без аутентификации блокируется. Флаг `--allow-nonloopback-http` допустим только за доверенным authenticated reverse proxy/tunnel. Для production необходимы HTTPS и server-side authentication/authorization на deployment boundary.

## 8. Проверка через MCP Inspector

После установки MCP SDK:

```bash
npx @modelcontextprotocol/inspector@latest
```

Подключить Streamable HTTP endpoint:

```text
http://127.0.0.1:8000/mcp
```

Проверить:

1. initialization;
2. наличие ровно четырёх Atlas tools;
3. read-only `atlas_system_status`;
4. `atlas_search_knowledge`;
5. `atlas_research` без изменения Resident state;
6. `atlas_research_and_learn` только с осознанным разрешением на сохранение опыта.

## 9. Подключение к ChatGPT Developer Mode

ChatGPT не подключается к локальному MCP напрямую. Для локального/приватного сервера предпочтителен OpenAI Secure MCP Tunnel; альтернативно нужен стабильный HTTPS deployment/tunnel. При использовании ngrok безопаснее явно переписать Host на локальный:

```bash
ngrok http 8000 --host-header=rewrite
```

В ChatGPT:

1. `Settings`;
2. `Security and login`;
3. включить `Developer mode`;
4. открыть `Plugins`;
5. добавить новый MCP/plugin connection;
6. указать HTTPS URL tunnel/deployment с окончанием `/mcp`.

Пример:

```text
https://<your-host>/mcp
```

После подключения выбирать Atlas plugin в новом чате.

## 10. Семантика state и безопасности ядра

`atlas_research` не commit-ит Resident state.

`atlas_research_and_learn` использует существующий механизм `ResidentCognitiveOrganism`. Само ядро проверяет, что mutable state не лежит внутри sealed runtime root. Стандартный внешний путь строится через `PHI_STATE_DIR`/XDG-compatible state location.

Gateway не имеет права:

- присваивать `ATLAS_NATIVE`;
- объявлять `ESTABLISHED_LAW`;
- объявлять мировой научный приоритет;
- обходить scientific promotion owner;
- выполнять неизвестные hardware actions;
- менять scientific owners или их алгоритмы.

## 11. Full vs summary response

По умолчанию `atlas_research*` возвращает ограниченное структурированное представление receipt:

```text
status
core_receipt_digest
semantic_typed_ir
competitive_set summary
information_gain status
selected experiment
representation invention status
primitive synthesis status
formal mathematical verification status / proof-obligation count
formal-kernel handoff status
counterexample-search summary
next_required_external_input
claim_boundary
```

Это предотвращает передачу в ChatGPT огромных внутренних receipts.

Если необходим полный core receipt:

```text
detail_level="full"
```

Полный receipt остаётся результатом самого Atlas; gateway только возвращает его без изменения.

## 12. Граница релиза

Базовый `RELEASE_MANIFEST.json` внутри исходного архива объявляет `0.15.29.0`, несмотря на имя исходного ZIP `15_24_0`.

До создания MCP-дистрибутива в исходном рабочем состоянии уже существовал post-seal delta:

- `source/lawspace/api.py`;
- `source/lawspace/long_horizon_scientific_cycle.py`;
- `source/lawspace/resident_cognitive.py`;
- новый `source/lawspace/experiment_execution.py`;
- новый `source/lawspace/measurement_adapters.py`;
- новый `evaluation/jhtdb_execution_adapter.py`;
- новый `evaluation/universal_experiment_qualification.py`.

Поэтому MCP-слой **не маскирует** состояние рабочей ветки как неизменённый старый seal. Для GitHub-merge полный список исходных файлов и SHA-256 хранится в manifest установочного patch-пакета; после установки canonical release-control пересобирается штатным `evaluation.build_release_controls`.

## 13. Проверки дистрибутива

При сборке выполняются:

- синтаксическая компиляция всех Python sources без создания `pyc`;
- импорт `LawSpaceAPI` и research contracts;
- read-only autonomous-research smoke;
- universal frozen-experiment qualification для уже присутствовавшего post-seal execution delta;
- MCP bridge smoke без SDK;
- проверка отсутствия `.venv`, `.git`, caches и installation metadata;
- SHA-256 inventory всех файлов чистого дистрибутива.

Дополнительно для gateway v1.2.0 проверено:

- повторный `atlas_research` с одинаковым запросом детерминирован по core receipt digest;
- при `commit_resident_state=False` файловое дерево дистрибутива не создаёт, не удаляет и не меняет файлов;
- при `commit_resident_state=True` и заданном `PHI_STATE_DIR` изменяется только внешний `resident_cognitive_state.json`, sealed tree остаётся неизменным;
- при штатном запуске gateway как script он устанавливает `sys.dont_write_bytecode=True` до импорта Atlas и не создаёт cache зависимостей; для module-import smoke используется `python -B`, чтобы не создавался cache самого gateway-модуля;
- read-only tools имеют явные `ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)`;
- `atlas_research_and_learn` помечен как state-changing, non-destructive, non-idempotent, closed-world tool;
- сигнатуры `MCPServer`, `ToolAnnotations` и Streamable HTTP сверены с официальным MCP Python SDK v2 и документацией OpenAI от 2026-09-27.

Полный wire-level запуск с внешним SDK/Inspector в build sandbox не был выполнен: sandbox не имеет DNS-доступа к PyPI, поэтому внешняя библиотека `mcp` сознательно не была подмешана в clean archive. Это остаётся runtime qualification, а не скрытый PASS.

## 14. MCP/OpenAI safety metadata

OpenAI использует MCP tool annotations при выборе подтверждений и отображении риска. В Atlas они задаются явно и соответствуют реальному поведению:

| Tool | readOnly | destructive | idempotent | openWorld |
|---|---:|---:|---:|---:|
| `atlas_system_status` | true | false | true | false |
| `atlas_search_knowledge` | true | false | true | false |
| `atlas_research` | true | false | true | false |
| `atlas_research_and_learn` | false | false | false | false |

`openWorld=false` относится только к текущему gateway: он работает с локальным bounded Atlas corpus и не предоставляет публичный web-search. Если в будущем research owner получит реальный open-web/tool access, annotation должна быть пересмотрена на уровне gateway metadata без изменения научного ядра.

## 15. Официальные спецификации

Актуальные reference pages:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/app-quickstart
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://github.com/modelcontextprotocol/python-sdk

Дата сверки документации: 2026-09-27.

## 16. Gateway 1.4.0: open-ended campaign без нового MCP tool

Количество внешних инструментов по-прежнему равно четырём.  Новый научный режим
не получил отдельный ChatGPT tool: он доступен через существующие
`atlas_research` и `atlas_research_and_learn`.

Добавлен необязательный аргумент:

```text
campaign_slice_budget: int = 1
```

При `campaign_slice_budget > 1` gateway вызывает существующий
`LawSpaceAPI.run_autonomous_research() with `campaign_slice_budget > 1``.  Это тот же
`ScientificResearchCycleOwner`, а не параллельный solver.

Также исправлена семантика пустых списков.  Явные

```text
required_domains=[]
target_axis_ids=[]
required_observables=[]
```

теперь передаются в ядро как явный VOID override.  Раньше falsy-проверка могла
удалить эти параметры на gateway boundary и позволить semantic router снова
назначить домен.  Это было неприемлемо для blind discovery.

`atlas_research` выполняет read-only campaign и переносит exact continuation
между slices в памяти. `atlas_research_and_learn` может дополнительно сохранить
тот же continuation через внешний Resident/Persistent Portfolio state.

Summary-ответ для campaign имеет schema
`atlas-mcp-open-ended-campaign-view/v1` и показывает число slices, уникальных
кандидатов/осей, continuation и compact view последнего research receipt.

MCP safety annotations не изменились.  `campaign_slice_budget` увеличивает объём
локального вычисления, но не открывает сеть и не даёт gateway права продвигать
научную истину.


## Semantic proof-obligation compiler: MCP boundary

`SEMANTIC-PROOF-OBLIGATION-COMPILER/1.0.0-COMPONENT` является внутренним read-only механизмом `PHI-MATHEMATICAL-INVENTION-KERNEL/1.4.0`. Он не добавляет пятый MCP tool и не переносит scientific control во внешний LLM. Существующие `atlas_research` / `atlas_research_and_learn` по-прежнему входят через authoritative `LawSpaceAPI.run_autonomous_research`; semantic compilation вызывается уже внутри Atlas. Внутренний API `compile_phi_semantic_proof_obligation` предназначен для диагностики/qualification и не присваивает theorem status. Публичная MCP-поверхность остаётся ровно из четырёх tools.
