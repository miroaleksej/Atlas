# Atlas 0.15.29.0: техническое руководство

<img width="1672" height="941" alt="95b0327d-f6c9-47be-939e-ad2657c838cb" src="https://github.com/user-attachments/assets/2aa004d6-2371-42ee-9cce-41036d0b2ed8" />

Это практическое руководство по запуску Atlas / Φ-Compiler / ScienceAtlas, поиску кандидатов научных законов, работе на стыке наук, проектированию экспериментов и расширению научного адресного пространства. Авторитетные ограничения системы определяют [MATHEMATICAL_CONTRACT.md](MATHEMATICAL_CONTRACT.md), [MATHEMATICAL_BOOK.md](MATHEMATICAL_BOOK.md) и [CLAIM_BOUNDARY.md](CLAIM_BOUNDARY.md).

> Atlas генерирует и проверяет гипотезы, но не превращает хорошую аппроксимацию в научный закон. Продвижение возможно только через единый доказательный путь U0–U10. Отсутствующие доказательства означают `PENDING` или `NEEDS_EXPERIMENT`, а не подтверждение и не опровержение.

## Содержание

- [1. Модель работы системы](#1-модель-работы-системы)
- [2. Установка и первый запуск](#2-установка-и-первый-запуск)
- [3. Основные способы запуска](#3-основные-способы-запуска)
- [4. Подготовка научной задачи и данных](#4-подготовка-научной-задачи-и-данных)
- [5. Поиск кандидатов законов](#5-поиск-кандидатов-законов)
- [6. Выбор алгоритма поиска](#6-выбор-алгоритма-поиска)
- [7. Междисциплинарный поиск](#7-междисциплинарный-поиск)
- [8. Построение и выбор экспериментов](#8-построение-и-выбор-экспериментов)
- [9. Проверка гипотезы и продвижение U0–U10](#9-проверка-гипотезы-и-продвижение-u0u10)
- [10. Добавление величин, осей и данных](#10-добавление-величин-осей-и-данных)
- [11. Добавление новой науки](#11-добавление-новой-науки)
- [12. Добавление закона, модели или гипотезы](#12-добавление-закона-модели-или-гипотезы)
- [13. Состояние, воспроизводимость и выпуск](#13-состояние-воспроизводимость-и-выпуск)
- [14. Карта всех возможностей](#14-карта-всех-возможностей)
- [Универсальность и потенциальные применения](#универсальность-и-потенциальные-применения)
- [15. Типовые рабочие сценарии](#15-типовые-рабочие-сценарии)
- [16. Диагностика ошибок](#16-диагностика-ошибок)
- [17. Справочник по всем тестам](#17-справочник-по-всем-тестам)

## 1. Модель работы системы

Atlas разделяет исследование на четыре слоя:

1. **Адресное пространство:** предметные области, научные оси, величины, единицы, точные семимерные размерности СИ, паспорта владельцев и типизированные мосты.
2. **Поиск:** конечные подмножества осей, точные π-группы, алгебраические и операторные грамматики, адаптивные оболочки, междисциплинарные композиции и открытый справедливый обход.
3. **Квалификация:** целостность, размерности, выводимость из известных моделей, качество аппроксимации, идентифицируемость, OOD, репликация, перестановочная нулевая проверка и различающий эксперимент.
4. **Состояние и доказательства:** контентные дайджесты, зафиксированные кандидаты, контракты измерений, внешние аттестации и квитанции продвижения.

Основной поток:

<img width="1672" height="941" alt="bb8ca5ce-048c-4041-9374-54a1572d6d8d" src="https://github.com/user-attachments/assets/c28540c1-2438-4508-8d21-ee55ddc8560d" />


Система имеет две полосы:

- **широкая полоса исследования** допускает неизвестные, неполные и рискованные кандидаты;
- **узкая полоса продвижения** требует всех обязательных доказательств и закрывается при их отсутствии.

### 1.1. Важно: 655 научных осей и 7 базовых размерностей — разные вещи

Текущий выпуск загружает **655 канонических научных осей в 13 предметных областях**. Это 654 базовые оси и одна каноническая динамическая ось. Система готова адресовать, сочетать и исследовать эти оси в локальных и междисциплинарных подпространствах.

Число **7** относится не к количеству научных осей, а только к длине вектора физической размерности в базисе СИ:

```text
(L, M, T, I, Θ, N, J)
```

Например, `physics.interaction_range`, `chemistry.reaction_diffusion_regime`, `biology.organisation_level` и `mathematics.geometric_structure` — разные научные оси. Если ось связана с физической величиной, её размерность при этом описывается семью компонентами. Семантическая, категориальная или формальная ось может вообще не быть физической величиной и потому не участвовать в размерностном ранге.

Фактически загружаемый реестр выпуска 0.15.29.0:

| Предметная область (`domain_id`) | Научных осей |
|---|---:|
| `aeronautics_and_aerostation` | 175 |
| `astronomy` | 13 |
| `biology` | 12 |
| `chemistry` | 78 |
| `earth_systems` | 12 |
| `materials_science` | 28 |
| `mathematics` | 20 |
| `mechanics` | 50 |
| `metrology` | 18 |
| `pharmaceutical` | 59 |
| `physics` | 103 |
| `quantum_information_and_computational_methods` | 75 |
| `systems_control` | 12 |
| **Всего** | **655** |

Проверить это непосредственно в установленной системе:

```python
from source.lawspace.domains import DOMAIN_REGISTRIES

print("Областей:", len(DOMAIN_REGISTRIES))
print("Осей:", sum(registry.axis_count for registry in DOMAIN_REGISTRIES.values()))
for domain_id, registry in sorted(DOMAIN_REGISTRIES.items()):
    print(domain_id, registry.axis_count)
```

Atlas не подставляет все 655 осей одновременно в одну регрессию. Это привело бы к комбинаторному взрыву и плохой идентифицируемости. Вместо этого система:

1. формирует локальные подпространства релевантных осей;
2. связывает оси с квалифицированными владельцами и величинами;
3. создаёт пары и многомерные комбинации внутри предметных областей и между ними;
4. использует типизированные мосты, мотивы совместного владения и семантические роли;
5. расширяет порядок подпространств адаптивно;
6. сохраняет состояние справедливого обхода, чтобы конечный запуск не считался пределом всего пространства;
7. отправляет каждый материализованный кандидат в общий доказательный путь.

В текущем запечатанном состоянии материализовано 3 706 адаптивных многомерных подпространств и 4 106 активных кандидатов фронтира. Среди них есть как однообластные, так и междисциплинарные комбинации. Поэтому архитектура 655 осей уже используется системой, а не является только будущей декларацией.

### 1.2. Адаптивное и многомерное рождение осей

Исследовательский цикл не ограничен добавлением ровно одной оси. Нормативный
контракт Atlas возвращается методом
`LawSpaceAPI.get_atlas_law_space_search_contract()` в поле
`axis_birth_cardinality_contract`:

```text
AXIS_BIRTH_CARDINALITY = ADAPTIVE
MULTI_AXIS_BIRTH = ALLOWED
HIGHER_ORDER_INTERACTION_AXES = ALLOWED
FIXED_AXIS_COUNT_PER_CYCLE = NONE
SEARCH = SPARSE + ADAPTIVE + OPEN_ENDED
```

Практически это означает следующий порядок работы:

1. Atlas выделяет разреженное локальное подпространство по типам величин,
   владельцам, доменам, мостам и структуре остатка.
2. Если эффект идентифицируется только совместно, цикл может номинировать
   конечный пакет из нескольких осей, включая interaction axes высокого порядка.
3. Размер пакета определяется задачей и доступным вычислительным бюджетом; в
   контракте нет фиксированного `1`, `2` или другого числа осей на цикл.
4. Каждая ось пакета отдельно проходит `assess_dynamic_axis`, проверку
   семантики, дубликатов, измеримости, provenance и затем обычный lifecycle.
5. Незавершённые ветви сохраняются для последующего fair-dovetail обхода и не
   объявляются ложными из-за окончания текущего бюджета.

Проверить политику программно:

```python
from source.lawspace.api import LawSpaceAPI

policy = LawSpaceAPI(".").get_atlas_law_space_search_contract()[
    "axis_birth_cardinality_contract"
]
print(policy)
```

`OPEN_ENDED` здесь не означает бесконечный массив или неограниченный один
запуск. Любой исполняемый цикл конечен. Неограниченным остаётся научный горизонт:
следующий цикл может открыть новый разреженный пакет осей, если того требует
структура задачи и имеются допустимые основания.

## 2. Установка и первый запуск

### Требования

- Python 3.11 или новее;
- POSIX-совместимая оболочка;
- Git;
- для notebook-примера — Jupyter;
- сеть нужна для установки зависимостей и внешних резолверов, но не для основного локального воспроизведения.

### Установка

```bash
git clone https://github.com/miroaleksej/Atlas.git
cd Atlas
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install --no-deps \
  ./extensions/ATLAS_AI_RESEARCH_EXTENSION_v0_10_0/dist/scienceatlas_ai-0.10.0-py3-none-any.whl
```

Команда `pip install -e .` устанавливает квалифицированный численный стек: NumPy `2.4.2`, SciPy `1.17.0` и SymPy `1.14.0`. Не обновляйте эти три пакета отдельно внутри запечатанного выпуска: изменение младших разрядов численного результата меняет контентные дайджесты фронтира. Новые версии библиотек должны проходить отдельную квалификацию с пересборкой release controls.

Для notebook и тестов:

```bash
python -m pip install pytest jupyter nbconvert
```

### Быстрая проверка

```bash
phi-compiler --help
python -c "from source.lawspace.api import LawSpaceAPI; print(LawSpaceAPI('.').runtime.current_release_id())"
make collect
make targeted
```

Ожидаемая версия — `0.15.29.0`. Актуальное число тестов следует проверять командой `pytest --collect-only -q`: оно растёт вместе с квалифицированными владельцами и сценариями.

### Где хранить изменяемое состояние

Запечатанное дерево проекта нельзя использовать как рабочее хранилище. Задайте внешний каталог:

```bash
export PHI_STATE_DIR=/absolute/path/outside/Atlas
```

По умолчанию используется `~/.local/state/phi-compiler/<release>/` либо `$XDG_STATE_HOME/phi-compiler/<release>/`.

## 3. Основные способы запуска

### CLI

Точка входа:

```bash
phi-compiler --help
```

Эквивалент из исходного кода:

```bash
python -m interfaces.phi_compiler_cli --help
```

### Автономный вопрос

Без записи состояния:

```bash
phi-compiler research "Какие безразмерные параметры управляют переносом и реакцией?" \
  --read-only-state \
  --output /tmp/atlas-research.json
```

С внешним постоянным состоянием:

```bash
phi-compiler research "Найди нерешённые координаты на стыке химии и физики" \
  --state-dir /tmp/atlas-state \
  --output /tmp/atlas-stateful.json
```

Естественный язык задаёт направление исследования, но не заменяет наблюдения, размерности и экспериментальные доказательства.

### Каталог и фронтир

```bash
phi-compiler --mode lawspace-query --query "Kepler" --limit 10
phi-compiler --mode lawspace-query --query "oscillation" --domain physics --limit 20
phi-compiler --mode candidate-query --domain physics --limit 20
```

Фильтры кандидатов:

```bash
phi-compiler --mode candidate-query \
  --domain physics \
  --generator EXACT_PAIR_FRONTIER \
  --category RELATIONAL \
  --risk MEDIUM \
  --source-owner OWNER-ID \
  --limit 50
```

Значения фильтров берите из существующих записей: неизвестное значение обычно даёт пустой результат, а не автоматически расширяет реестр.

### Квалификационные режимы

```bash
phi-compiler --mode lawspace
phi-compiler --mode candidate-scan
phi-compiler --mode synthetic --repeats 10 --workers 1 --shard-size 60
phi-compiler --mode hardware-twin
phi-compiler --mode physical-prebuild
phi-compiler --mode physical-adapter
phi-compiler --mode all-offline --output /tmp/atlas-all-offline.json
```

Без аргументов запускается `all-offline`. Реальный `physical-open-loop` в него не входит.

### Python API

```python
from source.lawspace.api import LawSpaceAPI

api = LawSpaceAPI(".")
print(api.runtime.current_release_id())
print(api.search_entities("diffusion", domain_id="physics", limit=10))
```

Перед использованием сложной поверхности запросите её контракт:

```python
print(api.get_scientific_axis_space_contract())
print(api.get_universal_law_discovery_contract())
print(api.get_scientific_promotion_contract())
```

Контракт сообщает владельца, схему, допустимый процесс и границы утверждений.

## 4. Подготовка научной задачи и данных

### Минимальный исследовательский контракт

До поиска зафиксируйте:

- вопрос и проверяемое утверждение;
- независимые переменные и целевой отклик;
- физический смысл каждой колонки;
- единицы и семимерную размерность `(L, M, T, I, Θ, N, J)`;
- системы/объекты, режимы и время измерения;
- неопределённости и ковариации;
- правила исключения строк и преобразований;
- разделение FIT, SEAL, OOD и независимой репликации;
- пространство подмножеств, грамматику формул и вычислительный бюджет;
- нулевую процедуру, число перестановок и уровень `α`;
- критерий фальсификации.

### Требования к табличным наблюдениям

Для `search_observations_for_law_candidates`:

- все столбцы имеют одинаковую длину;
- каждый поисковый признак имеет ровно семь целочисленных компонентов размерности;
- `target_name`, если задан, присутствует в `observations`;
- для логарифмического коллапса координата и цель положительны;
- категориальные данные не выдаются за физическую размерность;
- единицы заранее приведены к согласованной системе.

Порядок базиса:

```text
(L, M, T, I, Θ, N, J)
```

Примеры: длина `[1,0,0,0,0,0,0]`, время `[0,0,1,0,0,0,0]`, скорость `[1,0,-1,0,0,0,0]`, энергия `[2,1,-2,0,0,0,0]`.

### Поддерживаемые классы научных контейнеров

Контракт `get_scientific_data_ingestion_contract()` описывает JSON, CSV, TSV, NPY, NPZ, HDF5/NeXus, ROOT, ZIP, wheel, RO-Crate и Frictionless Data Package. Для воспроизводимого набора следует хранить:

- стабильный `dataset_id` и `artifact_id`;
- источник/DOI и локальный путь;
- ожидаемый SHA-256 или опубликованный checksum;
- ограничение размера;
- профиль схемы и обязательные поля/члены;
- дескрипторы наблюдаемых с `quantity_id`, ролью, единицей и масштабом приведения;
- адаптер, связывающий байты с типизированными величинами.

## 5. Поиск кандидатов законов

### 5.1. Поиск точных π-групп по собственным данным

```python
import numpy as np
from source.lawspace.api import LawSpaceAPI

rng = np.random.default_rng(11)
n = 360
D = 10 ** rng.uniform(-12, -8, n)
L = 10 ** rng.uniform(-5, -2, n)
k = 10 ** rng.uniform(-3, 1, n)
pi_true = L**2 * k / D
eta = np.tanh(np.sqrt(pi_true)) / np.sqrt(pi_true)

api = LawSpaceAPI(".")
result = api.search_observations_for_law_candidates(
    observations={"k": k, "D": D, "L": L, "eta": eta},
    dimensions={
        "k": [0, 0, -1, 0, 0, 0, 0],
        "D": [2, 0, -1, 0, 0, 0, 0],
        "L": [1, 0, 0, 0, 0, 0, 0],
    },
    target_name="eta",
    question="Что управляет эффективностью реакции и диффузии?",
    min_subset_size=2,
    max_subset_size=3,
    return_limit=25,
    permutation_count=100,
    permutation_seed=99,
)

print(result["candidates"][:3])
print(result["permutation_null"])
```

Алгоритм перечисляет указанные подмножества, строит точную рациональную матрицу размерностей, вычисляет её нуль-пространство, оставляет случаи `p = 1`, канонизирует показатели, устраняет математические дубликаты и ранжирует координаты по коллапсу цели. Перестановки повторяют всю поверхность уникальных кандидатов.

Интерпретация:

- `p = 0` — в выбранных величинах нет безразмерной группы;
- `p = 1` — единственная скалярная π-координата с точностью до масштаба и знака;
- `p > 1` — размерности дают семейство координат, но функцию нужно искать отдельно.

### 5.2. Поиск без целевого отклика

Уберите `target_name`. Результаты будут иметь вид `Π = C_DIMENSIONLESS`. Это структурные кандидаты на инвариантность; постоянство ещё требуется проверить между объектами, режимами и независимыми системами.

### 5.3. Поиск в научном пространстве осей

Для расширенного поиска с семантикой величин:

```python
result = api.search_atlas_law_space(
    variable_names=["D", "L", "k"],
    values=np.column_stack([D, L, k]).tolist(),
    target_values=eta.tolist(),
    target_name="eta",
    quantity_specs={
        "D": {"quantity_id": "QTY-DIFFUSIVITY", "dimension": [2,0,-1,0,0,0,0]},
        "L": {"quantity_id": "QTY-LENGTH", "dimension": [1,0,0,0,0,0,0]},
        "k": {"quantity_id": "QTY-INVERSE-TIME", "dimension": [0,0,-1,0,0,0,0]},
        "eta": {"quantity_id": "QTY-DIMENSIONLESS", "dimension": [0,0,0,0,0,0,0]},
    },
    domain_ids=("physics", "chemistry", "metrology"),
    search_shell=0,
)
```

`search_shell=0` сохраняет базовое поведение. Последующие оболочки расширяют порядок поддержки, показателей и разреженных термов; глобального фиксированного максимума нет, но каждый запуск конечен.

### 5.4. Работа с готовым фронтиром

```python
rows = api.search_candidates(domain_id="physics", limit=20)
candidate = api.get_candidate(rows[0]["candidate_id"])
quantities = api.resolve_candidate_quantities(candidate["candidate_id"])
```

Полезные методы:

- `search_candidates` — фильтрация активного фронтира;
- `get_candidate` — полная запись кандидата;
- `get_deep_formula_candidates` — кандидаты с более глубокими формулами;
- `get_scalar_law_birth_current` — зафиксированная перепись скалярных рождений;
- `candidate-scan` — повторная генерация и сравнение с реестром;
- `advance_atlas_dovetail_traversal(step_budget=N)` — следующая порция справедливого обхода.

`candidate-regenerate` изменяет создаваемое состояние и предназначен для подготовки нового снимка, а не обычного чтения.

### 5.5. Многокоординатный поиск при `p > 1`

Если размерностное ядро возвращает несколько независимых координат, используйте отдельный маршрут формы функции:

```python
result = api.search_observations_for_function_forms(
    observations=observations,
    dimensions=dimensions,
    target_name="response",
    group_ids=system_ids,
    permutation_count=99,
    permutation_seed=15250,
)
```

Метод фиксирует базис `Π₁, …, Πₚ`, перечисляет ограниченную поверхность структурных форм, проверяет ранг и обусловленность матрицы признаков, использует раздельную проверку качества и повторяет **весь** поиск при групповых перестановках. Не выбирайте одну красивую формулу до нулевой калибровки и не интерпретируйте синтетический контроль как доказательство закона реального мира.

### 5.6. Рождение нового языка функций по структуре остатка

В 0.15.27.0 метод `search_observations_for_function_forms` сначала выполняет прежний полиномиальный multi-Π поиск, получает строго out-of-fold прогноз и анализирует остаток. Если нормированная ошибка ниже порога рождения, текущая грамматика сохраняется. Если ошибка велика, но ни один операционный сигнал не превысил multiplicity-aware порог, расширение также запрещено. Только сочетание обоих условий передаёт запрос компоненту `FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT` существующего Mathematical Invention Kernel.

```python
result = api.search_observations_for_function_forms(
    observations=observations,
    dimensions=dimensions,
    target_name="response",
    axis_names=feature_names,
    hypothesis_budget=100,
    return_limit=20,
    permutation_count=99,
    permutation_seed=1729,
)

print(result["function_language_birth"])
print(result["hypotheses"][0]["function_family"])
```

Доступные конечные семейства: `RATIONAL`, `EXPONENTIAL`, `LOGARITHMIC`, `PERIODIC`, `PIECEWISE`, `KERNEL` и `LATENT`. Все зависящие от данных преобразования обучаются отдельно внутри тренировочной части fold. При перестановочной проверке заново выполняются полиномиальная аппроксимация, диагностика остатка, решение о рождении, аппроксимация порождённых языков и полное ранжирование. Запрещено один раз выбрать язык на наблюдаемой цели, а затем переставлять только коэффициенты.

Для отдельной проверки механизма:

```bash
python -m evaluation.function_language_birth_qualification
pytest -q -p no:cacheprovider tests/test_function_language_birth.py
```

Ожидаемый статус квалификатора — `PASS_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION`. Он подтверждает работу механизма на синтетических периодическом, локальном, полиномиальном и шумовом контролях, но не математическую новизну и не новый закон реального мира.

## 6. Выбор алгоритма поиска

| Научная ситуация | Рекомендуемый маршрут | Что получается |
|---|---|---|
| Есть численные данные и размерности | `search_observations_for_law_candidates` | точные уникальные π-кандидаты |
| Нужна семантика осей и несколько областей | `search_atlas_law_space` | типизированные отношения в научном пространстве |
| Нужно изучить существующий фронтир | `search_candidates` + `get_candidate` | готовые гипотезы и их статусы |
| Неизвестна недостающая координата | `run_axis_modeling` / динамическая ось | исследовательская ось-кандидат |
| `p > 1` или форма функции неизвестна | π-genesis, мономы/Лоран/Паде, универсальная грамматика | исполняемые представления |
| Нужны PDE/память/нелокальность | универсальная операторная грамматика | дифференциальные, интегральные, delay и graph-кандидаты |
| Нужны сочетания наук | typed bridges + composition path + multidomain search | междисциплинарная композиция |
| Нужно выбрать измерение | EIG или `design_phi_discriminating_experiment` | ранжированный контракт эксперимента |
| Нужно проверить научный статус | `qualify_frontier_promotion_path` | квитанция U0–U10 |

### Алгоритмы, реализованные в системе

1. **Точное ядро Бекингема–π:** рациональный ранг и нуль-пространство, канонизация целых показателей.
2. **Перебор подмножеств:** конечная поверхность от `min_subset_size` до `max_subset_size` с дедупликацией сигнатур.
3. **Коллапс данных:** логарифмические интервалы, внутригрупповой разброс `ln(y)`, нормировка на общий разброс.
4. **Адаптивные оболочки:** возрастающие поддержка, порядок показателей и бюджет разреженных выражений.
5. **Справедливое чередование:** возобновляемый append-only обход без фиксированного глобального потолка.
6. **Универсальная грамматика:** `+`, `-`, `*`, `/`, `exp`, `log`, рациональные/вещественные показатели, `sum`, `product`, `partial_t`, `gradient`, `laplacian`, `integral`, `delay`, `piecewise`, стохастические и графовые операторы.
7. **Поиск представления:** ограниченные мономиальные/лореновские формы и диагностика Паде по `sqrt(Π)` с разделением FIT/SEAL.
8. **Сравнение моделей:** качество, сложность MDL, структурная и практическая идентифицируемость, контролируемые пределы.
9. **Перестановочная нулевая проверка:** повтор полной адаптивной процедуры, а не только финальной формулы.
10. **Информационный выигрыш:** точный дискретный EIG только при явных прогнозных правдоподобиях.
11. **Различающий эксперимент:** максимизация средней дивергенции Йенсена–Шеннона при исполнимости, идентифицируемости и бюджете.

Не выбирайте алгоритм только по лучшей ошибке FIT. Для научного кандидата важны размерностная допустимость, простота, идентифицируемость, OOD, независимая репликация и устойчивость всей процедуры к нулевой модели.

## 7. Междисциплинарный поиск

Atlas не объединяет одинаково напечатанные символы автоматически. Перенос между науками выполняется через величины, роли, размерности, владельцев и типизированные мосты.

### Поиск сущностей в нескольких областях

```python
physics = api.search_entities("transport", domain_id="physics", limit=20)
chemistry = api.search_entities("transport", domain_id="chemistry", limit=20)
```

### Проверка символа и величины

```python
print(api.resolve_symbol("D"))
print(api.get_quantity("QTY-DIFFUSIVITY"))
print(api.find_by_dimensions(["2", "0", "-1", "0", "0", "0", "0"]))
```

Если `D` означает разные величины у разных владельцев, используйте `quantity_id` или `symbol_id`. Сходство обозначений не является мостом.

### Пути композиции и сравнение моделей

```python
paths = api.find_composition_path(
    source_domains=["physics", "chemistry"],
    target_type="DIMENSIONLESS_OBSERVABLE",
)
comparison = api.compare_models(["OWNER-A", "OWNER-B"])
```

### Обнаружение возможных мостов

```python
receipt = api.discover_phi_cross_domain_bridges(
    signatures=[
        {
            "owner_id": "PHYSICS-OWNER",
            "dimension_signature": "L2_T-1",
            "semantic_role": "TRANSPORT_COEFFICIENT",
            "operator_family": "DIFFUSIVE",
        },
        {
            "owner_id": "CHEMISTRY-OWNER",
            "dimension_signature": "L2_T-1",
            "semantic_role": "TRANSPORT_COEFFICIENT",
            "operator_family": "DIFFUSIVE",
        },
    ],
    minimum_score=0.92,
)
```

Обнаруженный мост — предложение структуры, не научное тождество. Для арифметической композиции нужен проверенный типизированный контракт. Исследование кортежей разных областей может начинаться без готового моста, но продвижение междисциплинарного отношения требует семантической и доказательной квалификации.

Специализированные поверхности уже существуют для нейтрино, авиации, квантового вакуума/гравитации, тензорной геометрии, чёрных дыр, частиц, фармацевтики и систем управления.

## 8. Построение и выбор экспериментов

### 8.1. Начинайте с конкурирующих гипотез

Хороший эксперимент должен давать различные предсказания хотя бы для двух зафиксированных моделей. До выбора измерения задайте:

- точные идентификаторы кандидатов;
- прогнозируемые исходы;
- измеряемые величины и единицы;
- область параметров и режим;
- стоимость и риск;
- критерий фальсификации;
- источник прогнозных вероятностей;
- независимую процедуру выполнения после фиксации.

### 8.2. Ранжирование по информационному выигрышу

```python
candidate_ids = ["CANDIDATE-A", "CANDIDATE-B"]
experiments = [
    {
        "experiment_id": "EXP-001",
        "measurements": ("response_at_high_control",),
        "outcomes": ("LOW", "HIGH"),
        "likelihoods": {
            "CANDIDATE-A": {"LOW": 0.9, "HIGH": 0.1},
            "CANDIDATE-B": {"LOW": 0.2, "HIGH": 0.8},
        },
        "cost": 1.0,
        "risk_penalty": 0.0,
    }
]

ranked = api.rank_experiments_by_information_gain(
    candidate_ids=candidate_ids,
    experiment_specs=experiments,
    priors={"CANDIDATE-A": 0.5, "CANDIDATE-B": 0.5},
)
```

Для реального вызова идентификаторы должны существовать в каталоге кандидатов. В каждом эксперименте:

- не менее двух исходов;
- строка likelihood для каждого кандидата и только для него;
- одинаковый набор исходов во всех строках;
- неотрицательные конечные значения с положительной суммой;
- положительная конечная стоимость;
- неотрицательный штраф риска.

Без явных прогнозных likelihood система возвращает `BLOCKED_PREDICTIVE_LIKELIHOODS_REQUIRED` и не выдумывает EIG.

### 8.3. Автоматический различающий эксперимент

```python
contract = api.get_phi_discriminating_experiment_contract()

design = api.design_phi_discriminating_experiment(
    question="Какое измерение различит новую теорию и базовые модели?",
    candidate_theory=candidate_theory_artifact,
    baseline_theories=[baseline_a, baseline_b],
    cost_budget=100.0,
)
```

Теории должны быть исполняемыми артефактами ожидаемой схемы, а не произвольными текстовыми формулами. Внутренний процесс фиксирует теории, строит конечный набор запросов, получает предсказания только через среду выполнения теорий, проверяет исполнимость/идентифицируемость/стоимость и выбирает максимум средней дивергенции Йенсена–Шеннона.

Выбранный протокол не является результатом эксперимента. Измерение выполняет внешний прибор или типизированный адаптер после фиксации.

### 8.4. Портфель экспериментов

После исследовательского цикла и EIG-квитанции:

```python
portfolio = api.rank_post_gate_experiment_portfolio(
    research_cycle_receipt=cycle,
    information_gain_receipt=ranked,
    resource_metrics={
        "EXP-001": {"money": 10.0, "time": 2.0, "risk": 0.1}
    },
    scenario={"money_weight": 1.0, "time_weight": 0.5},
)

quadrants = api.post_gate_experiment_quadrants(
    portfolio_receipt=portfolio,
    eig_threshold_bits=0.2,
    cost_threshold=20.0,
)
```

Портфель помогает выбирать, но не отменяет жёсткие доказательные барьеры.

### 8.5. Реальное оборудование

Последовательность безопасности:

```bash
phi-compiler --mode hardware-twin
phi-compiler --mode physical-prebuild --contract hardware/PHYSICAL_STAND.json
phi-compiler --mode physical-adapter --contract hardware/PHYSICAL_STAND.json
```

Только после независимой проверки контракта, серийного номера, пределов, изоляции и разрешения оператора:

```bash
phi-compiler --mode physical-open-loop \
  --contract hardware/PHYSICAL_STAND.json \
  --host DEVICE_HOST \
  --expected-serial DEVICE_SERIAL \
  --raw-output /absolute/external/path/raw.json \
  --operator-approved
```

### 8.6. Реальный EDA-эксперимент по оптимизации микросхемы

Начиная с 0.15.26.0 Atlas содержит исследовательского владельца `EDA-CHIP-DESIGN-RESEARCH/1.0.0`. Он фиксирует пространство четырёх параметров физического проектирования, общий начальный набор и равные бюджеты, затем сравнивает `ATLAS_QUERY_FUNCTION_FORM` с `RANDOM`, `GRID` и `BAYESIAN_GP_EI` на реальном потоке `sky130hd/gcd`.

Проверка backend и запуск:

```python
from source.lawspace.api import LawSpaceAPI

api = LawSpaceAPI(".")
print(api.get_eda_chip_backend_status(
    orfs_flow_root="/absolute/path/to/OpenROAD-flow-scripts/flow",
    runner="auto",
))

receipt = api.run_eda_chip_design_pilot(
    orfs_flow_root="/absolute/path/to/OpenROAD-flow-scripts/flow",
    runner="auto",
    evaluation_budget=14,
    warm_start_count=12,
    candidate_pool_size=256,
    seed=15260,
)
print(receipt["status"], receipt["comparison"])
```

Эквивалентный CLI-обёртка — `evaluation/eda_chip_pilot.py`. На GitHub настоящий контейнерный запуск выполняет ручной workflow **Atlas CMOS GCD PPA Pilot**. ORFS/Yosys/OpenROAD/KLayout остаются авторитетными исполнителями синтеза, размещения, трассировки, DRC и LVS; Atlas отвечает за фиксацию эксперимента, стратегию поиска, сбор метрик и доказательную квитанцию. Без полного timing, финальных DRC/LVS и GDS результат закрывается как неполный. Недоступный backend возвращает `CHIP_PILOT_BACKEND_UNAVAILABLE` и никогда не заменяется синтетической PPA-моделью.

### 8.7. Адаптивная сортировка, песочница и «что если?»

Выпуск 0.15.28.0 добавляет `RESEARCH-TRIAGE-SANDBOX/1.0.0` для работы с перспективными, но ещё недостаточно доказанными результатами. Это вспомогательная поверхность принятия исследовательских решений, а не новый владелец научного продвижения. Авторитетный маршрут U0–U10 по-прежнему принадлежит только `SCIENTIFIC-PROMOTION-CORE/9.2.0`.

Сначала оцените качество данных:

```python
from source.lawspace.api import LawSpaceAPI

api = LawSpaceAPI(".")
quality = api.assess_research_data_quality(
    n_points=120,
    relative_uncertainty=0.04,
    domain="materials_science",
)
print(quality["quality_tag"], quality["information_density"])
```

Atlas присваивает один из рабочих тегов:

- `STRICT` — более 1 000 наблюдений и неопределённость менее 1%; строгие пороги `rho*=0.05`, `sigma*=0.05`;
- `EMPIRICAL` — промежуточное качество; маршрут `PHENOMENOLOGICAL_MODEL`, пороги `rho*=0.15`, `sigma*=0.10`;
- `EXPLORATORY` — менее 30 наблюдений или неопределённость более 10%; маршрут `STRUCTURAL_ANOMALY` только в песочнице.

Если неопределённость не передана, результат принудительно остаётся исследовательским: `UNCERTAINTY_UNDECLARED_ASSIGNED_EXPLORATORY`. Поле `information_density` помогает определить приоритет, но не является вероятностью истинности.

Для сортировки нескольких гипотез используйте:

```python
ranking = api.rank_exploration_sandbox(hypotheses=[
    {
        "candidate_id": "CANDIDATE-A",
        "rho_adj": 0.08,
        "simplicity_score": 0.9,
        "cross_consistency": 0.8,
        "familywise_p": 0.02,
        "alpha_fwer": 0.05,
    },
])
print(ranking["ranked_hypotheses"])
```

DPI объединяет качество аппроксимации, простоту, межсистемную согласованность и FWER-штраф с весами `0.35 / 0.20 / 0.30 / 0.15`. `DPI >= 0.70` означает только `PROMISING_REJECT`: кандидат стоит исследовать дальше, но он не проходит U5 или U6. Координаты `accuracy`, `simplicity`, `uniqueness` можно передать встроенной 3D-карте из `static/index.html`; визуальная позиция не является доказательством.

Поиск пробелов измерений:

```python
plan = api.propose_sandbox_what_if_experiments(
    axis_summaries=[{
        "axis_id": "temperature",
        "observed_min": 250.0,
        "observed_max": 350.0,
        "target_min": 200.0,
        "target_max": 500.0,
        "sensitivity": 0.8,
        "relative_uncertainty": 0.03,
    }],
    count=2,
)
```

Планировщик ранжирует незакрытые диапазоны по размеру пробела, чувствительности и неопределённости. Каждое предложение имеет `world_result_observed=false` и `proposal_is_evidence=false`, пока измерение действительно не выполнено.

Совет гипотез поддерживает `NOTE`, `SPONSOR_REVIEW`, `REJECT`, `FRESH_IDEA_LINK` и `REQUEST_SANDBOX_DIMENSION_EXCEPTION`. Изменяющие вызовы пишут журнал только во внешний каталог `PHI_STATE_DIR`:

```python
decision = api.record_hypothesis_council_action(
    candidate_id="CANDIDATE-A",
    action="SPONSOR_REVIEW",
    reason="Нужен отдельный OOD-режим",
    expert_id="EXPERT-01",
    feature_snapshot={
        "accuracy": 0.92,
        "simplicity": 0.75,
        "cross_consistency": 0.60,
        "fwer_penalty": 0.20,
    },
)
```

`SPONSOR_REVIEW` возвращает кандидата к сбору доказательств и никогда не выставляет U6. Запрос исключения размерности действует только в песочнице и оставляет U2 закрытым. После восьми размеченных решений система может рекомендовать новые веса DPI; применение выполняется отдельным методом `apply_hypothesis_council_weight_recommendation` и не меняет строгие веса продвижения.

Изолированная квалификация подсистемы:

```bash
make research-triage
```

## 9. Проверка гипотезы и продвижение U0–U10

| Этап | Проверка |
|---|---|
| U0 | целостность записи и дайджеста |
| U1 | типизированная гипотеза и привязка модели |
| U2 | точная размерностная квалификация |
| U3 | соглашения, единицы и артефакты |
| U4 | известная выводимость и совпадение с предшествующими работами |
| U5 | fit, коллапс или инвариантность |
| U6 | отдельный OOD-режим |
| U7 | независимые системы |
| U8 | перестановочная нулевая проверка полного конвейера |
| U9 | выполненный научно различающий эксперимент |
| U10 | численное ядро продвижения |

Проверка будущей записи фронтира:

```python
receipt = api.qualify_frontier_promotion_path(record, controls={})
print(receipt["status"])
```

Прямой численный вызов не может обойти единую квитанцию фронтира. U8 требует минимум 200 перестановок и `α = 0.01` по текущему контракту. Неопределённость без модели блокирует статистическое продвижение. Полный ранг сам по себе недостаточен: проверяется масштабированное отбеленное SVD и минимальное сингулярное значение.

Различайте результаты:

- `LAW_CANDIDATE` — прошли все применимые барьеры;
- `NEEDS_EXPERIMENT` / `PENDING` — не хватает доказательств;
- `NON_IDENTIFIABLE` / `UNDERDETERMINED` — данные не разделяют параметры или модели;
- `FALSIFIED` — пройден явный заранее объявленный критерий опровержения;
- `REJECTED` — запись нарушила структурный/доказательный контракт.

Неудача продвижения не равна опровержению.

## 10. Добавление величин, осей и данных

### 10.1. Новая величина

Канонические величины находятся в `data/quantities/registry.json`. Запись содержит:

```json
{
  "quantity_id": "QTY-EXAMPLE",
  "name_ru": "пример величины",
  "canonical_unit": "m s^-1",
  "ontology_reference": "QUDT-3.5.0:quantitykind:Example",
  "dimension": {
    "length": "1",
    "mass": "0",
    "time": "-1",
    "current": "0",
    "temperature": "0",
    "amount": "0",
    "luminous_intensity": "0"
  },
  "digest": "<канонический SHA-256 записи>"
}
```

Не копируйте заглушку digest. Каноническое изменение реестра — операция подготовки выпуска: используйте существующую схему/построитель, проверьте уникальность `quantity_id`, онтологическую ссылку, единицу и точную размерность, затем выполните тесты и пересоберите контроли.

### 10.2. Исследовательская динамическая ось

Безопасный первый шаг — оценка без изменения реестра:

```python
proposal = {
    "proposal_id": "PROP-NEW-AXIS-001",
    "domain_id": "physics",
    "axis_id": "example_measurable_axis",
    "description_ru": "Новая измеримая координата",
    "value_kind": "CONTINUOUS_RANGE",
    "physical_or_information_meaning": "Что именно представляет координата",
    "measurement_protocol": "Как её независимо измерить",
    "units_or_normalization": "SI: m/s",
    "expected_range": {"minimum": 0.0, "maximum": 100.0},
    "falsifiable_advantage": "Как ось улучшает OOD-прогноз и когда это опровергается",
    "redundancy_test": "Как проверяется отсутствие эквивалентной оси",
    "allowed_values": (),
    "provenance_evidence": ("SOURCE-ID",),
}

admission = api.assess_dynamic_axis(proposal)
print(admission["status"])
```

Допустимые `value_kind`: `ENUM`, `HIERARCHICAL_ENUM`, `MULTI_ENUM`, `BOOLEAN`, `INTEGER`, `RATIONAL`, `CONTINUOUS_RANGE`, `DIMENSION_VECTOR`, `SYMBOLIC_EXPRESSION`, `ONTOLOGY_REFERENCE`, `GRAPH_REFERENCE`, `DISTRIBUTION`, `TEXT`.

`ADMITTED_PROVISIONAL_RESEARCH_AXIS` не изменяет канонический реестр. Для канонического продвижения нужны семантический класс, отсутствие дубликата, центральная проверка, идентифицируемость или авторитетный источник, OOD/релевантность, независимая репликация или несколько источников, фальсифицируемость и внешняя world-attestation. Единственная точка мутации — `promote_dynamic_axis`; сначала используйте `mutate=False`.

```python
dry_run = api.promote_dynamic_axis(proposal, validation, mutate=False)
```

### 10.3. Новые данные

Для быстрого локального исследования не нужно менять реестр: загрузите CSV/JSON/NumPy самостоятельно, приведите колонки к массивам и передайте их в `search_observations_for_law_candidates`.

Для воспроизводимого набора выпуска:

1. сохраните исходный артефакт в подходящем `data/external/...`;
2. добавьте декларативный источник, checksum, лимит размера и профиль схемы;
3. создайте дескрипторы наблюдаемых с quantity ID, единицами и ролями;
4. реализуйте/зарегистрируйте типизированный адаптер;
5. разделите наблюдения, отклик, covariance/nuisance и метаданные;
6. добавьте тест целостности, схемы, семантики и численного контроля;
7. зафиксируйте источник до раскрытия результата;
8. выполните квалификацию и пересборку печати.

### 10.4. Жизненный цикл оси

Для существующей динамической оси доступны:

- `get_dynamic_axis_registry_state` — состояние реестра;
- `assess_phi_axis_lifecycle` — оценка перехода статуса;
- `commit_phi_axis_lifecycle` — явная запись прошедшего перехода;
- `resolve_phi_axis_lifecycle` — история конкретной оси.

Изменение, замена, разделение или слияние осей должно сохранять прежние идентичности и квитанции; молчаливая подмена запрещена.

## 11. Добавление новой науки

Скопируйте шаблон:

```bash
cp data/domains/domain_manifest.template.json.txt data/domains/new_science.json
```

Минимальный манифест:

```json
{
  "schema": "phi-domain-plugin-manifest/v1",
  "domain_id": "new_science",
  "domain_role": "natural_science",
  "description_ru": "Новая предметная область",
  "axis_schema_version": "1",
  "common_rules_owner": "COMMON-SCIENTIFIC-RULES/1.0.0",
  "axes": [
    {
      "axis_id": "example_axis",
      "description_ru": "Координата новой области",
      "value_kind": "TEXT",
      "allowed_values": [],
      "required_for": [],
      "forbidden_for": [],
      "provenance": "DOMAIN_OWNER"
    }
  ],
  "entity_profiles": [],
  "constraints": [],
  "owner": {
    "module": "source.lawspace.new_science",
    "class": "NewScienceDomainOwner"
  }
}
```

`owner` необязателен, если достаточно декларативных осей. Он нужен для собственных уравнений, семантических преобразований, совместимости или моделей эксперимента.

Новая область не должна копировать общие механизмы проверки источников, доказательств, новизны, EIG и продвижения. Они принадлежат центральным владельцам. Изменять `source/lawspace/domains.py` для нового плагина не требуется. После добавления манифеста перезапустите процесс.

Проверка:

```python
print(api.list_domain_plugins())
print(api.get_domain_plugin_contract("new_science"))
```

Для рождения новой науки из исследовательского состояния существуют `assess_phi_domain_birth` и `commit_phi_domain_birth`; для эволюции — оценка/фиксация разделения и слияния областей. Commit-методы являются явными мутациями и требуют доказательных квитанций.

## 12. Добавление закона, модели или гипотезы

### 12.1. Безопасное предложение гипотезы

```python
proposal = api.propose_candidate({
    "epistemic_state": "PENDING_PROPOSAL",
    "claim_origin": "RESEARCHER_HYPOTHESIS",
    "statement": "Проверяемая зависимость ...",
    "domain_id": "physics",
    "observables": ["QTY-LENGTH", "QTY-TIME"],
    "falsification_criterion": "Заранее объявленный критерий ...",
})
```

Этот вызов не изменяет активный реестр и не разрешает продвижение. Нельзя присвоить через него `ATLAS_NATIVE` или состояние установленного закона.

### 12.2. Паспорт исходного закона

Квалифицированный паспорт должен включать:

- стабильные `owner_id`, `domain_id`, `name_ru` и класс сущности;
- эпистемический статус;
- формулу и разбираемое представление;
- каждый символ с уникальным `symbol_id`, физическим смыслом, ролью, `quantity_id`, единицей и размерностью;
- допущения и область применимости;
- контролируемые пределы;
- наблюдаемые и модель неопределённости;
- происхождение, источник и классификационную уверенность;
- контентные дайджесты и тесты.

Новая гипотеза должна начинаться в ожидающем состоянии. `ESTABLISHED_LAW` допустим только для квалифицированного внешнего источника, а не для автоматически предложенной формулы.

### 12.3. Компиляция теории

Общий путь:

```text
типизированная гипотеза
  → synthesize_phi_executable_representation
  → compile_phi_theory
  → execute_phi_compiled_theory
  → контролируемые пределы и квалификация
  → различающий эксперимент
```

Перед вызовами получите `get_phi_theory_compiler_contract()`. Артефакт теории и его freeze digest должны оставаться неизменными между построением прогноза и экспериментом.

### 12.4. Известная выводимость и новизна

Литературный поиск выполняйте после фиксации кандидата. `assess_post_derivation_novelty` требует `candidate_freeze_digest`. Совпадение с известным законом сохраняется как выводимость/предшествующая работа; отсутствие совпадения не доказывает новизну. Известный источник не должен подсказывать слепому селектору формулу после начала поиска.

## 13. Состояние, воспроизводимость и выпуск

### Восстановление состояния

```bash
phi-compiler resident-state-restore \
  --snapshot /path/to/snapshot.json \
  --expected-sha256 EXPECTED_HEX \
  --state-dir /absolute/external/state \
  --overwrite-state
```

`--overwrite-state` используйте только при намеренной замене. Путь внутри репозитория будет отклонён.

### После контролируемого изменения

```bash
make collect
make targeted
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 \
OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
pytest -q -p no:cacheprovider
make release-controls
make seal-audit
make audit-read-only
```

`make release-controls` пересчитывает `RELEASE_MANIFEST.json`, `capabilities.json`, `invariants.json`, `HASHES.txt` и `FILE_TREE.md`. Не редактируйте создаваемые дайджесты вручную.

Read-only воспроизведение фронтира разделяет две проверки. Байтовый SHA prior-art сопоставляется с действительно запечатанным файлом ledger, который не должен изменяться. Повторное вычисление на другой BLAS/libm-платформе отдельно обязано вернуть тот же полный набор типизированных идентичностей кандидатов, классов, областей, владельцев и эпистемических статусов. Диагностический `replay_sha256` может отличаться из-за незначащих младших разрядов численных payload; семантическое расхождение по-прежнему является ошибкой и не игнорируется.

### Тяжёлое воспроизведение

```bash
make full
```

Оно формирует план, запускает изолированные свежие процессы и агрегирует `reports/FULL_HEAVY_REPLAY_CURRENT.json`.

## 14. Карта всех возможностей

### Каталог, размерности и кандидаты

- поиск сущностей, паспортов, символов, величин и констант;
- поиск по точной размерности и домашней ячейке;
- пути композиции и сравнение моделей;
- активный фронтир, глубокие формулы и скалярная перепись;
- точный Buckingham-π и поиск по наблюдениям;
- адаптивное пространство научных осей;
- открытый справедливый обход и персистентное состояние.

### Представления и теория

- алгебраические, трансцендентные, дифференциальные, интегральные, delay, piecewise, stochastic и graph-операторы;
- математическое изобретение примитивов и морфизмов;
- поиск неизвестного представления;
- синтез, компиляция и исполнение теорий;
- анализ контролируемых пределов;
- ресурсная теория вычислительных маршрутов.

### Доказательства и эксперименты

- динамическая оценка качества данных `STRICT` / `EMPIRICAL` / `EXPLORATORY`;
- DPI-ранжирование и 3D-карта исследовательской песочницы без полномочий продвижения;
- планирование «что если?» по пробелам диапазонов и внешний журнал совета гипотез;
- центральная проверка доказательных пакетов и внешних источников;
- U0–U10 и численный конвейер продвижения;
- OOD, независимая репликация, идентифицируемость и перестановочные нулевые проверки;
- EIG, портфель экспериментов и различающий эксперимент;
- привязка кандидата к данным, проекция отклика, выполнение измерения и world-attestation;
- prospective external validation по зафиксированному файлу и внешнему аудиту.

### Области и специализированные владельцы

- механика, физика, химия, астрономия, материаловедение, авиация/аэростатика, математика, метрология, системы управления и фармацевтика;
- атомные электронные и многочастичные состояния;
- ядерное связывание и распады;
- Daya Bay, KATRIN, T2K и Super-Kamiokande;
- пространство частиц и коллайдерные проверки;
- чёрные дыры, динамика Эйнштейна, тензорная геометрия и память кривизны;
- квантовый вакуум и гравитационные пересечения;
- авиационные мосты и нелокальные временные/пространственные ядра;
- фармацевтические гипотезы, селективность и problem atlas.

### Эволюция научного пространства

- предварительное и каноническое добавление динамических осей;
- жизненный цикл, замена и история осей;
- рождение, разделение и слияние предметных областей;
- обнаружение междисциплинарных мостов;
- когнитивное и резидентное внешнее состояние;
- эволюция знаний, длительные циклы и ресурсно-зависимый выбор действий;
- рефлексивная архитектура, контролируемое самовосстановление и developmental open-endedness.

Эти поверхности имеют разные полномочия. Наличие исполняемого метода не означает установленный научный результат; проверяйте контракт и поле `status` каждого ответа.

## Универсальность и потенциальные применения

Atlas универсален на уровне исследовательского процесса: одна и та же типизированная архитектура связывает вопрос, 655 научных осей, 13 областей, наблюдения, размерности, модели, алгоритмы поиска, внешние вычислители, эксперименты и доказательства. Новая задача не обязана помещаться в готовый шаблон закона — для неё можно добавить величины, оси, предметный плагин, грамматику представления, измерительный адаптер и собственника квалификации, сохранив единый fail-closed контур.

Практически это открывает широкий класс потенциальных задач:

- поиск инвариантов, безразмерных комплексов, законов подобия и масштабирования;
- восстановление скрытых координат и недостающих наблюдаемых;
- скалярная и multi-Π регрессия, символьные, операторные, дифференциальные, интегральные, графовые и стохастические представления;
- междисциплинарный перенос структуры через типизированные мосты без смешения разных физических смыслов;
- сравнение теорий, анализ пределов, причинных альтернатив и областей применимости;
- активное планирование измерений, EIG, портфели различающих экспериментов, OOD и межсистемная репликация;
- цифровые двойники, управление, технологические режимы, материалы, аэрокосмические системы, фармацевтические маршруты и EDA-оптимизация площади/мощности/задержки;
- построение контентно-адресуемых научных баз, воспроизводимых вычислительных протоколов и проверяемых исследовательских выпусков.

Возможности расширения действительно велики, но их нужно отличать от уже подтверждённых результатов. Новый владелец или алгоритм даёт исполняемую исследовательскую поверхность; научное утверждение появляется только после подходящих данных, внешней проверки и всех обязательных барьеров U0–U10.

## 15. Типовые рабочие сценарии

### Сценарий A: данные есть, формулы нет

1. Зафиксируйте колонки, единицы и размерности.
2. Очистите данные по заранее объявленным правилам.
3. Отделите цель и независимые системы.
4. Запустите точный поиск π-групп по ограниченным подмножествам.
5. Дедуплицируйте и зафиксируйте поверхность кандидатов.
6. Выполните перестановочную нулевую проверку всей процедуры.
7. Проверьте OOD и постоянство между системами.
8. Сопоставьте с известными выводами после фиксации.
9. Спроектируйте различающий эксперимент.
10. Передайте полный пакет в U0–U10.

### Сценарий B: известна гипотеза, нужно проверить

1. Создайте `PENDING_PROPOSAL`.
2. Типизируйте символы, величины, единицы и область применимости.
3. Объявите альтернативы и критерий фальсификации.
4. Выполните точную размерностную проверку.
5. Скомпилируйте исполняемые предсказания.
6. Зафиксируйте FIT/SEAL/OOD до оценки.
7. Проверьте идентифицируемость и неопределённости.
8. Получите независимую репликацию и выполненное измерение.
9. Запустите единую квалификацию фронтира.

### Сценарий C: закон возможен на стыке наук

1. Найдите сущности отдельно в каждой области.
2. Разрешите символы в `quantity_id` и роли.
3. Сопоставьте размерности, операторные семейства и области применимости.
4. Найдите путь композиции или предложите типизированный мост.
5. Запустите `search_atlas_law_space` с несколькими `domain_ids`.
6. Сравните внутридисциплинарные и междисциплинарные альтернативы.
7. Проверьте, что мост не смешивает разные физические величины.
8. Проведите OOD и репликацию в независимых системах обеих областей.

### Сценарий D: остаток модели указывает на недостающую ось

1. Убедитесь, что остаток не объясняется единицами, шумом, смещением или режимом.
2. Сформулируйте измеримый смысл новой оси.
3. Объявите протокол, диапазон, нормировку, преимущество и тест избыточности.
4. Выполните `assess_dynamic_axis`.
5. Добавьте ось только локально и проверьте complexity-penalized OOD gain.
6. Получите независимую репликацию и world-attestation.
7. Выполните dry-run продвижения и лишь затем явную каноническую мутацию.

## 16. Диагностика ошибок

### Не найден кандидат

Проверьте порядок базиса размерностей, одинаковую длину колонок, размер подмножеств и режим `p`. При `p > 1` переключитесь с поиска единственной π-группы на контролируемый поиск функции.

### Символ неоднозначен

```python
api.resolve_symbol("D")
```

Используйте `quantity_id`, `symbol_id` и владельца, а не одиночную букву.

### Невозможно посчитать коллапс

Проверьте положительность координаты и цели, ненулевую дисперсию `ln(y)` и число заполненных логарифмических интервалов.

### Нулевая проверка не имеет нужного разрешения

Для семейного уровня требуется `1/(n_perm + 1) ≤ α`. Увеличьте число перестановок; недостаточное разрешение не является прохождением.

### Ось не принимается

Изучите `gates` и `redundancy_candidates` в квитанции. Частые причины: неизвестная область, дубликат `axis_id`, нет измерительного протокола, диапазона, фальсифицируемого преимущества или теста избыточности.

### EIG заблокирован

Не хватает явных прогнозных likelihood для каждого кандидата и исхода. Текстовое сходство или придуманные вероятности не допускаются.

### Путь состояния отклонён

Он находится внутри запечатанного дерева. Перенесите его во внешний абсолютный каталог.

### После изменения не проходит печать

```bash
git diff --check
make release-controls
make seal-audit
make audit-read-only
```

Если изменение не планировалось, сначала исследуйте `git diff`, `HASHES.txt` и `RELEASE_MANIFEST.json`, не перезаписывая исходные данные.

## 17. Справочник по всем тестам

В выпуске 0.15.29.0 после интеграции DNS-эксперимента собирается **131 тест** (число собранных случаев может быть больше числа функций из-за параметризации). Ниже описан каждый тест: что проверяется, каким способом и какой результат считается успешным. Идентификатор после имени файла можно передать `pytest` для отдельного запуска:

```bash
pytest -q -p no:cacheprovider \
  tests/test_eda_chip_design.py::test_eda_backend_fail_closed_without_orfs
```

Обозначение «ожидается PASS» означает прохождение программных утверждений теста, а не автоматическое подтверждение научного закона.

### `tests/test_adaptive_axis_discovery.py` — 12 тестов

- `test_scan_finds_context_axis_without_mutating_registry` — запускает поиск контекстной оси и сравнивает состояние реестра до и после. Ожидается обнаруженный кандидат при неизменном каноническом реестре.
- `test_positive_causal_readiness_requires_positive_generalization_contract` — подаёт положительное причинное свидетельство без полного контракта обобщения. Ожидается запрет статуса causal-ready до выполнения всех условий.
- `test_tlr7_causal_readiness_rejects_normalized_ig_shortcut` — проверяет TLR7-сценарий с нормированной информационной ценностью. Ожидается, что высокий IG не заменит репликацию и причинную проверку.
- `test_p2x7_high_ig_is_not_causal_readiness_without_replication_and_generalization` — повторяет отрицательный контроль для P2X7. Ожидается сохранение исследовательского статуса без ложной причинной готовности.
- `test_provisional_axis_mount_is_local_only` — монтирует предварительную ось в локальный контекст и повторно читает глобальный реестр. Ожидается локальная доступность без глобальной мутации.
- `test_common_rules_preserve_candidate_and_axis_incompleteness_boundaries` — пропускает неполного кандидата и ось через общие правила. Ожидается явная фиксация неполноты без преобразования неизвестности в ложность.
- `test_failed_axis_promotion_is_unverified_candidate_not_false_axis` — моделирует непройденное продвижение оси. Ожидается статус непроверенного кандидата, а не утверждение, что ось не существует.
- `test_axis_modeling_does_not_birth_interaction_with_train_constant_axis` — обучает модель при постоянной на FIT оси. Ожидается отсутствие ложной рождённой интеракции, неидентифицируемой по обучающим данным.
- `test_first_blind_real_physics_cycle_replays` — воспроизводит зафиксированный слепой физический цикл и проверяет его квитанции и метрики. Ожидается детерминированный PASS без заявления нового закона.
- `test_adaptive_research_kernel_can_birth_multiple_dormant_axes_in_one_cycle` — строит ответ, которому одновременно нужны две dormant-оси, и проверяет полный subset search. Ожидается активация ровно `z` и `w`, `selected_cardinality = 2`, разрешённый multi-axis birth и отсутствие фиксированного числа осей на цикл.
- `test_large_dormant_space_switches_to_sparse_forward_backward_search_without_cardinality_ceiling` — создаёт большое dormant-пространство, превышающее exhaustive trial budget. Ожидается переход на sparse forward/backward search, восстановление `z` и `w` и явная фиксация, что ресурсный бюджет не является научным потолком cardinality.
- `test_residual_driven_language_expansion_discovers_hidden_two_factor_coordinate` — запускает Level-4 incomplete-representation control. Ожидается persistent residual на depth 1, автоматическое открытие depth 2, восстановление скрытой двухфакторной координаты и sealed OOD PASS без causal promotion. Дополнительно проверяется верхняя provenance-квитанция: `atlas_native=true`, полный набор обязательных полей, а также привязка `code_digest` и `result_digest`.

### `tests/test_curvature_memory_current.py` — 2 теста

- `test_curvature_memory_owner_survives_clean_baseline_without_postfreeze_seed` — открывает владельца памяти кривизны в чистом состоянии без послезаморозочного seed. Ожидается доступный владелец и отсутствие заранее материализованного ответа.
- `test_curvature_memory_api_and_claim_boundary` — вызывает публичный API и проверяет поля границы утверждений. Ожидается исполняемый ответ при `scientific_truth_established = false`.

### `tests/test_domain_plugin_architecture.py` — 7 тестов

- `test_minimal_manifest_loads_without_central_registry_edit` — создаёт минимальный предметный manifest во временном каталоге и загружает его обычным механизмом плагинов. Ожидается регистрация без правки центрального реестра.
- `test_manifest_must_delegate_common_rules` — удаляет обязательную ссылку на владельца общих правил. Ожидается отказ загрузки.
- `test_manifest_cannot_shadow_generic_rules` — пытается переопределить общенаучные правила внутри предметного плагина. Ожидается fail-closed ошибка.
- `test_duplicate_axes_fail_closed` — объявляет повторяющиеся идентификаторы осей. Ожидается отклонение неоднозначного manifest.
- `test_partial_owner_declaration_fails` — задаёт неполную пару module/class владельца. Ожидается ошибка вместо частичной регистрации.
- `test_pharmaceutical_plugin_delegation_is_ready` — загружает фармацевтический plugin и проверяет делегирование общих функций. Ожидается готовый предметный владелец с общим научным маршрутом.
- `test_common_rules_is_router_not_parallel_solver` — инспектирует роль общих правил. Ожидается маршрутизация к владельцам, а не второй независимый решатель тех же задач.

### `tests/test_eda_chip_design.py` — 6 тестов

- `test_eda_backend_fail_closed_without_orfs` — запускает проверку в пустом временном каталоге. Ожидается `EDA_BACKEND_UNAVAILABLE`/`CHIP_PILOT_BACKEND_UNAVAILABLE`, отсутствие суррогата и отсутствие результата чипа.
- `test_orfs_metric_parser_requires_explicit_lvs` — создаёт синтетическую структуру ORFS с метриками, но без однозначной LVS-квитанции. Ожидается `lvs_pass = null/false` и закрытый sign-off.
- `test_route_drc_cannot_substitute_for_missing_signoff_drc` — предоставляет route-stage DRC без финального sign-off DRC. Ожидается, что маршрутная диагностика не засчитывается как прохождение DRC.
- `test_missing_setup_violation_count_fails_timing_closed` — задаёт slack без явного числа setup-нарушений. Ожидается непройденный timing gate.
- `test_eda_control_compares_four_equal_budget_strategies` — использует квалификационный evaluator и сравнивает Atlas, random, grid и Bayesian GP/EI. Ожидаются общий warm start, равные бюджеты и четыре отдельные квитанции без физического chip-claim.
- `test_eda_owner_is_exposed_through_single_lawspace_api` — проверяет `READ_TOOLS` и вызывает контракт/backend через `LawSpaceAPI`. Ожидаются три публичных EDA-метода и единый авторитетный владелец.

### `tests/test_electronic_state_space_current.py` — 6 тестов

- `test_electronic_state_space_contract_has_no_answer_order_or_fixed_shell_ceiling` — читает контракт электронного пространства. Ожидается отсутствие таблицы правильного порядка и фиксированного научного потолка оболочек.
- `test_scf_evaluator_has_no_internal_configuration_generator_or_nuclear_radius_law` — инспектирует границы SCF-evaluator. Ожидается, что он оценивает переданную конфигурацию, но не генерирует её и не подмешивает закон ядерного радиуса.
- `test_electronic_state_space_light_atom_executes_without_answer_table` — запускает лёгкий атом без answer-bearing fixture. Ожидается исполняемый численный результат с честным статусом.
- `test_public_api_exposes_new_authoritative_owner_not_as_regression` — сверяет классы инструментов API. Ожидается электронный владелец в обычной читающей поверхности, а не в карантине regression tools.
- `test_theory_compiler_many_body_coordinate_discovery_is_rank_adaptive_and_named_method_free` — запускает компилятор многочастичной координаты при изменяемом ранге. Ожидается адаптивный выбор структуры без подсказки названием известного метода.
- `test_evidence_born_many_body_coordinate_survives_precommitted_blind_atoms` — фиксирует координату до проверки на слепых атомах и воспроизводит контроль. Ожидается сохранение кандидата и прохождение заранее объявленной проверки без постфактум-подгонки.

### `tests/test_epoch_genesis_autonomous.py` — 7 тестов

- `test_pipeline_null_exact_p_and_resolution_gate` — вычисляет точное перестановочное p-value и проверяет условие разрешения `1/(n+1) ≤ α`. Ожидается PASS только при достаточном числе перестановок.
- `test_rational_schedule_has_correct_resolution_and_is_summable_prefix` — строит рациональное распределение alpha по эпохам и суммирует конечный префикс. Ожидаются требуемое разрешение и расход не выше общего бюджета.
- `test_scoped_binding_is_fail_closed_until_director_binds_fingerprints` — подаёт свидетельство без привязки fingerprint директором. Ожидается блокировка его использования.
- `test_duplicate_fingerprints_are_refused` — повторно предъявляет тот же evidence fingerprint. Ожидается отказ от двойного учёта.
- `test_blind_autonomous_path_reaches_honest_resource_frontier_without_false_claim` — выполняет слепой автономный поиск до вычислительного предела. Ожидается `RESOURCE_DEFERRED` и отсутствие ложного открытия.
- `test_noise_is_not_promoted_before_the_same_resource_yield` — запускает сопоставимый шумовой контроль. Ожидается отсутствие продвижения шума до того же ресурсного рубежа.
- `test_deferred_resource_yields_before_buying_another_confirmation_epoch` — проверяет политику планировщика после исчерпания бюджета. Ожидается возврат управления с запросом ресурса, а не скрытая покупка следующей эпохи.

### `tests/test_exoplanet_dimensional_closure_example.py` — 10 тестов

- `test_example_notebook_is_current_release` — исполняет все code cells notebook и проверяет metadata выпуска 15.25.0, а также фильтрацию локальных артефактов. Ожидается корректный notebook формата 4, совместимый с 0.15.28.0.
- `test_example_dataset_schema_and_size` — читает CSV и проверяет 50 строк и фиксированный набор столбцов. Ожидается точное соответствие схеме примера.
- `test_example_dataset_has_positive_observations` — проверяет конечность и положительность величин для логарифмического анализа. Ожидается отсутствие недопустимых значений.
- `test_example_search_surface_is_complete` — сверяет число рассмотренных гипотез и полноту заранее объявленного перебора. Ожидается 172 гипотезы без сокращения до показанного shortlist.
- `test_example_freezes_unhinted_kepler_coordinate` — проверяет победившие показатели `(3, -2, -1)` без передачи формулы Кеплера. Ожидается зафиксированная координата до реестрового сопоставления.
- `test_example_generates_gravitational_dimension` — выводит размерность отсутствующей константы из цели и предикторов. Ожидается `L³ M⁻¹ T⁻²`.
- `test_example_closes_exact_rational_kernel_at_p1` — добавляет порождённую величину и пересчитывает точное рациональное ядро. Ожидается нуль-дефектность `p = 1` и замыкающая сигнатура.
- `test_example_postfreeze_registry_match` — сопоставляет зафиксированный результат с реестром только после поиска. Ожидается распознавание гравитационной константы без утечки ответа в поиск.
- `test_example_numeric_control_is_within_declared_scale` — сравнивает оценку `G` с контрольным значением. Ожидается относительная ошибка в объявленном допустимом диапазоне.
- `test_example_receipt_preserves_claim_boundary` — инспектирует финальную квитанцию. Ожидается воспроизведённый контроль без утверждения нового закона, новой константы или prospective validation.

### `tests/test_function_language_birth.py` — 8 тестов

- `test_mathematical_invention_kernel_exposes_function_language_component_without_new_owner` — читает контракты Mathematical Invention Kernel и компонента рождения языка. Ожидается один существующий authority, компонент `FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT` и отсутствие фиксированного глобального каталога как первичного пространства.
- `test_polynomial_control_does_not_birth_unneeded_language` — подаёт хорошо описываемую полиномом поверхность с малым шумом. Ожидается `CURRENT_LANGUAGE_RESIDUAL_WITHIN_BIRTH_TOLERANCE`, ноль порождённых языков и OOF NRMSE ниже `0.04`.
- `test_periodic_residual_births_language_and_beats_polynomial_grammar` — сравнивает прежнюю полиномиальную грамматику и адаптивный поиск на скрытой синусоидальной поверхности. Ожидается рождение `PERIODIC`, OOF NRMSE ниже `0.20`, улучшение более чем в 3,3 раза и конечный исполняемый прогноз.
- `test_local_bivariate_residual_births_kernel_language` — подаёт сумму двух локальных двумерных экспоненциальных областей. Ожидается язык `KERNEL` по координатам `{0,1}`, NRMSE ниже `0.55` и не более 70% ошибки полиномиального baseline.
- `test_dynamic_language_birth_is_replayed_inside_permutation_null` — запускает пять перестановок периодической задачи. Ожидается повтор всей полиномиальной и порождённой поверхности на каждой перестановке и сохранённая граница отсутствия world-law/novelty claim.
- `test_structureless_residual_does_not_force_language_birth` — подаёт независимый нормальный шум с высокой ошибкой baseline. Ожидается `NO_OPERATION_SIGNAL_ABOVE_BIRTH_GATE`, пустой список языков и ноль порождённых гипотез.
- `test_operator_language_birth_uses_translation_meta_primitives_not_differential_catalog` — запускает operator-language birth из локального переноса, алгебры и dimension typing. Ожидаются rank shells 1–3, отсутствие каталога именованных производных и отсутствие фиксированного глобального потолка operator rank.
- `test_operator_language_can_expand_pointwise_carrier_depth_without_named_term_catalog` — сравнивает carrier depth 1 и 2. Ожидается рождение двухфакторной typed composition только во втором shell и явное отсутствие научного потолка глубины.

### `tests/test_permutation_eprocess_current.py` — 2 теста

- `test_permutation_eprocess_full_qualification` — воспроизводит полную квалификацию перестановочного e-process, включая группы C6/S6 и эмпирическую калибровку. Ожидается `PASS_PERMUTATION_EPROCESS_15_20_0` при сохранённой границе «только для одной цели».
- `test_reused_epoch_is_refused_and_does_not_change_genesis_journal` — повторно использует уже израсходованную эпоху и сравнивает журнал до и после. Ожидается отказ и байтовая неизменность genesis journal.

### `tests/test_query_driven_research_current.py` — 4 теста

- `test_query_mode_recovers_thiele_coordinate_without_formula_hint` — генерирует реакционно-диффузионные данные и запускает перебор размерных подмножеств без формулы. Ожидается первое место `L²k/D`, полный учёт кандидатов и перестановок.
- `test_question_focus_fails_closed_on_ambiguous_bare_symbols` — передаёт неоднозначные односимвольные обозначения. Ожидается ошибка с требованием quantity ID вместо произвольного выбора смысла.
- `test_query_mode_p_gt_1_searches_function_form_and_replays_full_surface` — запускает multi-Π контроль с `p = 4`, 45 структурными гипотезами и групповыми перестановками. Ожидается rank-1 модель, полный replay поверхности и familywise `p = 0.01`.
- `test_scalar_query_reports_p_gt_1_deferred_instead_of_silently_dropping_it` — подаёт многокоординатную задачу скалярному маршруту. Ожидается явный `p_gt_1_deferred_to_function_form_lane`, а не пустой или ложный отрицательный ответ.

### `tests/test_research_triage.py` — 5 тестов

- `test_quality_tiers_and_information_density` — оценивает три набора с большим, средним и малым объёмом данных при разных неопределённостях. Ожидаются теги `STRICT`, `EMPIRICAL`, `EXPLORATORY`, соответствующие пороги `rho*`/`sigma*` и информационная плотность в диапазоне `[0, 1]`.
- `test_dpi_is_rank_only_and_weighted` — рассчитывает DPI для сильной по диагностическим признакам гипотезы и проверяет границы результата. Ожидается значение от 0 до 1 и неизменный запрет `dpi_can_promote_scientific_status = false`.
- `test_expert_sponsor_cannot_pass_u6` — записывает действие эксперта `SPONSOR_REVIEW` в пустой журнал совета. Ожидается `authoritative_u_gate_override = false` и возврат к сбору доказательств, а не прохождение U6.
- `test_dimension_exception_is_sandbox_only` — запрашивает исключение размерности для спорной классификации единиц. Ожидается эффект `SANDBOX_ONLY_U2_REMAINS_CLOSED`: исследование разрешено только в песочнице, U2 не меняется.
- `test_what_if_identifies_uncovered_ranges` — задаёт наблюдавшийся диапазон `[0, 1]` внутри целевого `[-1, 2]` и просит два эксперимента. Ожидаются две заявки для нижнего и верхнего незакрытых диапазонов без объявления их результатами измерений.

### `tests/test_science_atlas_core.py` — 2 теста

- `test_science_atlas_core_owner_is_preserved_but_prior_materialization_is_absent` — проверяет доступность ядра ScienceAtlas и чистоту хранилища результатов. Ожидается живой владелец без восстановленных исторических materialization.
- `test_atomic_frontier_prior_receipt_is_not_shipped_in_clean_baseline` — ищет прежнюю атомную frontier-квитанцию в поставке. Ожидается её отсутствие при сохранённой возможности заново выполнить исследование.

### `tests/test_scientific_axis_space_current.py` — 11 тестов

- `test_scientific_axis_contract_is_atlas_native_not_symbolic_regression` — читает контракт пространства осей. Ожидается первичность типизированных осей и владельцев, а не неограниченного дерева выражений.
- `test_gaussian_state_scaling_birth` — подаёт гауссов контроль и запускает точный размерностный поиск. Ожидается воспроизводимая координата масштабирования с корректной сигнатурой.
- `test_relativistic_spacetime_axis_birth` — выполняет контроль рождения релятивистской пространственно-временной оси. Ожидается типизированная ось и точная размерностная квалификация.
- `test_orientational_thermal_additive_short_circuit` — проверяет случай аддитивного теплового вклада в ориентационной задаче. Ожидается раннее распознавание простой структуры без ложной сложной связи.
- `test_evidence_born_rational_response` — строит рациональный отклик из данных и проверяет его на зафиксированной части. Ожидается доказательно рождённый кандидат с исполняемой формой.
- `test_reusable_scientific_coordinates_live_in_canonical_atlas_registry` — извлекает повторно используемые координаты из канонического реестра. Ожидаются стабильные ID и отсутствие локальных дубликатов.
- `test_public_api_exposes_authoritative_atlas_law_space_and_compat_adapter_only` — сверяет API основной поверхности и compatibility adapter. Ожидается один авторитетный маршрут без параллельного решателя.
- `test_core_convergence_exact_kernel_uses_canonical_seven_dimensional_basis` — проверяет матрицу размерностей и делегирование точному ядру. Ожидается базис `(L,M,T,I,Theta,N,J)` и рациональная арифметика.
- `test_legacy_five_dimensional_descriptor_is_boundary_compatibility_only` — передаёт старый пятикомпонентный дескриптор через compatibility boundary. Ожидается нормализация на границе без превращения 5D в каноническое ядро.
- `test_local_law_space_execution_budgets_are_shells_not_scientific_ceilings` — выполняет поиск с конечным локальным бюджетом и читает контракт продолжения. Ожидается остановка текущей оболочки, но отсутствие заявления об исчерпании науки.
- `test_conservation_invariant_canonicalization_uses_composition_not_constancy_alone` — сравнивает постоянство траектории и композиционную аддитивность. Ожидается канонизация закона сохранения только при композиционном свидетельстве.

### `tests/test_scientific_exploitation_current.py` — 5 тестов

- `test_all_u4_candidates_have_u5_u10_execution_dossiers` — перечисляет 447 материализованных U4-гипотез и их следующие этапы. Ожидается отдельное U5–U10 dossier для каждой записи.
- `test_ai_extension_is_executable_but_not_promotion_authority` — вызывает AI-расширение и сверяет разрешённые статусы. Ожидается исполняемое предложение при отсутствии полномочий научного продвижения.
- `test_manual_candidate_prediction_lowering_is_frozen_and_heldout_failure_is_preserved` — фиксирует ручное lowering до раскрытия held-out данных и воспроизводит неудачу коллапса. Ожидается сохранённый отрицательный результат без повторной настройки.
- `test_u4_structural_lowerability_audit_is_data_independent_and_frozen` — выполняет аудит структурной сводимости без чтения целевых наблюдений. Ожидаются замороженные числа single-owner, multi-owner и blocked кандидатов.
- `test_second_distinct_manual_lowering_requires_alpha_ledger` — запрашивает вторую отличающуюся ручную попытку. Ожидается блокировка без явного учёта множественности и расхода alpha.

### `tests/test_tensor_axisymmetric_current.py` — 1 тест

- `test_tensor_einstein_owners_remain_live_while_old_receipts_are_absent` — проверяет владельцев тензорной геометрии и динамики Эйнштейна, одновременно ища старые result receipts. Ожидаются живые методы и чистое отсутствие исторических ответов.

### `tests/test_unified_current.py` — 39 тестов

- `test_current_runtime_registry_is_snapshot_not_ceiling` — загружает runtime и пересчитывает оси, области, паспорта и пустые baseline-хранилища. Ожидаются 655 осей, 13 областей, 445 законов и трактовка снимка как продолжимого состояния.
- `test_preexisting_domain_owners_remain_live` — вызывает владельцев чёрных дыр, Эйнштейна, нейтрино, частиц, фармацевтики, аэрокосмоса и квантового вакуума. Ожидаются доступные контракты всех ранее существовавших областей.
- `test_typed_bridge_can_transfer_or_refuse_without_merging_axes` — проверяет допустимый и недопустимый междисциплинарный перенос. Ожидается типизированная передача либо явный отказ без слияния разных осей.
- `test_current_api_exposes_adaptive_kernel_and_preserves_domain_surfaces` — сверяет публичные методы API адаптивного ядра и предметных владельцев. Ожидается полная поверхность без удаления прежних возможностей.
- `test_current_release_tree_and_book_are_single_authority` — сопоставляет release identity, математическую книгу и файлы управления выпуском. Ожидается одна согласованная версия и одна нормативная математическая основа.
- `test_global_axis_space_is_open_ended_not_619_fundamental` — проверяет фактические 655 осей, открытое пространство и машиночитаемый контракт рождения осей. Ожидаются `ADAPTIVE`, разрешение multi-axis/higher-order birth, отсутствие фиксированного числа осей на цикл, политика `SPARSE + ADAPTIVE + OPEN_ENDED` и обязательный индивидуальный lifecycle каждой оси.
- `test_owner_connected_search_reuses_existing_strong_gravity_owners` — запускает связанный поиск сильной гравитации. Ожидается повторное использование зарегистрированных владельцев вместо создания теневых копий.
- `test_atomic_frontier_is_regression_owner_not_persisted_seed` — проверяет классификацию атомного контрольного пути и baseline-файлы. Ожидается regression-only владелец без предзагруженного ответа.
- `test_adaptive_research_kernel_is_current_authority_without_fixed_ceiling` — читает контракт адаптивного ядра и его бюджеты. Ожидается единый authority и отсутствие фиксированного глобального потолка.
- `test_temperature_axis_is_added_to_space_before_any_formula_coupling` — проверяет последовательность рождения температурной оси. Ожидается регистрация оси до проверки формульной связи.
- `test_representation_activation_is_explicitly_not_causal_establishment` — активирует скрытую координату по residual improvement и одновременно проверяет причинный статус. Ожидается `REPRESENTATION_ACTIVATED`, но `CAUSALLY_NOT_ESTABLISHED`, пустые causal-ready/established списки и запрет automatic causal selection.
- `test_assistant_cannot_assign_atlas_native_claim_origin` — имитирует попытку ассистента выставить авторитетный claim origin. Ожидается отказ полномочий.
- `test_representation_gap_can_synthesize_executable_operator_without_named_law` — передаёт пробел представления без имени известного закона. Ожидается синтез исполняемого оператора-кандидата с ограниченным claim.
- `test_representation_gap_entry_is_executable_without_fabricated_observations` — исполняет созданный оператор на явных входах. Ожидается численный результат без генерации вымышленных наблюдений.
- `test_public_api_surface_is_complete_and_regressions_are_quarantined` — сравнивает READ/MUTATION/REGRESSION списки с ожидаемой поверхностью. Ожидается полнота API и изоляция answer-bearing контролей.
- `test_open_ended_periodic_frontier_has_no_numeric_z_ceiling_and_fails_closed_without_prefix` — исследует периодический фронтир без достаточного префикса. Ожидается отсутствие численного потолка Z и честная блокировка при нехватке данных.
- `test_every_current_source_module_imports_cleanly` — импортирует каждый Python-модуль `source`, создаёт все доменные registries и восемь типизированных handlers. Ожидается отсутствие ошибок импорта и точный набор регистраций.
- `test_post118_identifiability_is_set_valued_and_relativistic_axis_active` — проверяет post-118 электронную задачу с несколькими допустимыми конфигурациями. Ожидается множественный идентифицируемый набор и активная релятивистская ось, а не один подсказанный ответ.
- `test_open_ended_nuclear_world_is_evidence_first_and_has_no_numeric_ceiling` — открывает ядерный мир и инспектирует политику расширения. Ожидается приоритет аттестованных данных и отсутствие жёсткого потолка нуклидов.
- `test_nuclear_world_advances_only_with_attested_lifetime_and_never_treats_absence_as_nonexistence` — подаёт запись времени жизни с аттестацией и без неё. Ожидается продвижение только первой; отсутствие данных остаётся неизвестностью.
- `test_first_post_clean_atlas_native_experiment_replays_and_stays_not_law` — воспроизводит первый Atlas-native синтетический эксперимент. Ожидается PASS механизма при `new_physical_law_established = false`.
- `test_low_frequency_gust_anomaly_is_quantified_without_false_mechanism_promotion` — анализирует публичный аэродинамический остаток 4–8 Гц и проектирует трёхсостоянийный эксперимент. Ожидаются зафиксированные метрики аномалии без продвижения причинного механизма.
- `test_frontier_scan_preserves_every_materialized_candidate_without_promotion` — пересчитывает весь активный фронтир и проверяет классы, глубины и 4 106 записей. Ожидается `PASS_ATLAS_FRONTIER_CANDIDATE_SCAN`, сохранение кандидатов и ноль автопродвижений.
- `test_algebraic_frontier_polynomial_identity_is_global_sign_canonical` — создаёт эквивалентные полиномиальные тождества с противоположным знаком. Ожидается одна каноническая сигнатура.
- `test_frontier_replay_is_read_only_for_persisted_candidate_ledger` — хеширует ledger до и после replay. Ожидается одинаковый SHA-256 и успешный scan.
- `test_frontier_candidate_ledger_is_current_research_state_not_baseline_registry` — сопоставляет активный ledger с baseline runtime registry. Ожидаются 4 106 исследовательских записей отдельно от пустого канонического baseline.
- `test_every_current_frontier_candidate_has_one_valid_fail_closed_promotion_path` — валидирует U0–U10 receipt каждой записи. Ожидается ровно один корректный маршрут на кандидата и отсутствие обхода обязательных барьеров.
- `test_whole_pipeline_null_is_computed_and_unified_path_can_become_prepromotion_ready` — строит положительный квалификационный контроль со всем перестановочным replay. Ожидается достижимость prepromotion-ready только после точного whole-pipeline null.
- `test_numeric_scientific_promotion_cannot_bypass_unified_frontier_receipt` — напрямую вызывает численное ядро без валидной общей квитанции. Ожидается отказ продвижения.
- `test_fair_dovetail_release_snapshot_preserves_15_13_frontier_and_has_no_hidden_ceiling` — проверяет состояние планировщика, сохранённые legacy-ID и fairness contract. Ожидается сохранение 1 005 ранних кандидатов и отсутствие скрытого потолка.
- `test_fair_dovetail_runtime_advance_is_external_append_only_and_does_not_modify_seal` — направляет mutable state во временный каталог, выполняет шаги и хеширует seal. Ожидается append-only внешнее состояние и неизменное дерево выпуска.
- `test_owner_axis_binding_overlay_recovers_only_qualified_existing_owner_semantics` — применяет overlay привязки владельцев к осям. Ожидается восстановление только квалифицированной существующей семантики без изобретения величин.
- `test_materialized_relational_hypotheses_reach_u4_and_fail_closed_at_u5_world_evidence` — прогоняет материализованные реляционные гипотезы через барьеры. Ожидается U4 для 447 записей и остановка на U5 без мировых данных.
- `test_current_frontier_advances_by_depth_without_auto_promotion` — делает следующий шаг глубины фронтира. Ожидаются новые/углублённые исследовательские записи без автоматического law promotion.
- `test_resident_state_versions_are_separate_and_snapshot_restore_is_digest_bound` — создаёт внешний снимок, проверяет версии компонента/схемы/выпуска и пробует restore с digest. Ожидается разделение версий и восстановление только при совпадающем SHA-256.
- `test_materialized_hypotheses_execute_u4_and_fail_closed_at_world_evidence` — исполняет U4-аудит и проверяет terminal/next-gate статусы. Ожидается сохранённая неизвестность U5–U10 вместо ложного PASS или falsification.
- `test_genesis_evidence_scoped_open_search_invariants` — проверяет инварианты областей alpha, fingerprint evidence, глубины shell и bounded materialisation. Ожидается отсутствие cross-subsidy, повторного учёта и скрытого научного потолка.

## Краткая памятка

```text
1. Сначала контракт и фиксация задачи.
2. Затем типизация величин, единиц и размерностей.
3. Потом полный заранее объявленный поиск.
4. Зафиксировать кандидатов до литературы и эксперимента.
5. Сравнить с альтернативами, проверить идентифицируемость.
6. FIT не смешивать с SEAL/OOD/репликацией.
7. Нулевую проверку выполнять для всей процедуры.
8. Эксперимент должен различать модели и быть выполнен после фиксации.
9. Недостающие доказательства означают ожидание.
10. Канонические изменения и научное продвижение — только через владельца полномочий.
```

# Ручной слепой эксперимент Навье—Стокса (`0.15.28.0`)

## Назначение

Эксперимент `evaluation/navier_stokes_blind_experiment.py` проверяет не знание Atlas названия известного уравнения, а текущую способность Adaptive Research Kernel восстановить локальную структуру динамического баланса из обезличенных численных наблюдений, активировать недостающую dormant-координату по остаточной структуре и перенести найденное замыкание на независимый sealed holdout.

Это **контрольный reference-world benchmark**, а не доказательство существования и гладкости решений Навье—Стокса. Он также не является утверждением о новом физическом законе. `ATLAS_NATIVE` в квитанции означает только корректное происхождение результата из исполненного ядра Atlas.

## Что получает Atlas

Для каждого из двух импульсных каналов Atlas получает только маскированные величины одинаковой размерности `L T^-2`:

- target `r0`;
- начальные активные координаты `a07`, `a12`, `a19`;
- dormant-координаты `a23`, `a31`, `a37`.

Физические названия этих столбцов и контрольное уравнение не входят в request. Вопрос формулируется как поиск типизированного локального баланса неизвестного континуума. После формирования execution receipt маска декодируется только в блоке `postfreeze_decoding`.

Третий канал независимо проверяет локальное closure-соотношение двух маскированных скоростей деформации `c05` и `c11` размерности `T^-1`.

## Reference world

Генератор создаёт четыре семейства точных двумерных несжимаемых потоков с различными структурами баланса: затухающий периодический вихрь, жёсткое вращение, затухающий однонаправленный сдвиг и стационарный параболический канальный профиль. Они нужны одновременно: одно семейство само по себе может давать вырожденную идентифицируемость коэффициентов.

Discovery и sealed части имеют разные значения амплитуд, пространственных масштабов, вязкости, времени и параметров потока. Поэтому sealed-проверка проверяет перенос на невиданные параметры, а не повтор тех же строк.

До вызова Atlas reference world проходит внутренний self-check: максимум невязки импульсного баланса и дивергенции должен быть меньше `1e-12`.

## Установка

Из корня распакованного release:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

В Windows PowerShell активация:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Для воспроизводимости рекомендуется отключить сторонние pytest plugins и ограничить BLAS одним потоком, как это делает `Makefile`.

## Предварительная проверка release

```bash
python -c "from source.lawspace.api import LawSpaceAPI; print(LawSpaceAPI('.').runtime.current_release_id())"
python -m interfaces.phi_compiler_cli audit-read-only
```

Текущая версия системы должна соответствовать `0.15.29.0`; сам retained benchmark сохраняет идентичность `0.15.28.0`. Обратите внимание: имя внутреннего каталога исторически содержит `15_24_0`, поэтому идентичность release проверяется по `pyproject.toml`/runtime, а не по имени папки.

## Основной запуск

На macOS/Linux:

```bash
make navier-stokes-experiment
```

или напрямую:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python -m evaluation.navier_stokes_blind_experiment \
  --output reports/NAVIER_STOKES_BLIND_EXPERIMENT_CURRENT.json \
  --summary
```

На Windows PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
python -m evaluation.navier_stokes_blind_experiment `
  --output reports/NAVIER_STOKES_BLIND_EXPERIMENT_CURRENT.json `
  --summary
```

## Что должно появиться

Единственный основной артефакт ручного запуска:

```text
reports/NAVIER_STOKES_BLIND_EXPERIMENT_CURRENT.json
```

Его и нужно передать для последующего анализа. Файл содержит полный execution receipt обоих импульсных каналов и closure-канала, digest замороженных requests, список residual-axis candidates, выбранную dormant-ось, коэффициенты, внутренний holdout, sealed OOD holdout, provenance firewall и post-freeze decode.

## Критерии PASS

Верхний статус должен быть:

```text
PASS_BLIND_CONTINUUM_BALANCE_RECOVERY
```

Ключевые признаки корректного результата:

1. начальная модель без `a23` имеет заметную held-out ошибку;
2. residual discovery ранжирует `a23` как необходимую координату;
3. активируется именно `a23`, а `a31`/`a37` остаются distractors;
4. после активации коэффициенты маскированного баланса близки к `(-1,-1,-1,+1)`;
5. обе компоненты проходят sealed OOD holdout с `NRMSE < 1e-10`;
6. closure-канал восстанавливает коэффициент `-1` между `c05` и `c11`;
7. `scientific_law_established=false` сохраняется.

## Что прислать для анализа

Достаточно файла:

```text
reports/NAVIER_STOKES_BLIND_EXPERIMENT_CURRENT.json
```

Если запуск завершился ошибкой до создания JSON, сохраните полный terminal output и traceback. Не редактируйте JSON вручную: digest нужен для проверки воспроизводимости.

## Адаптивное рождение нескольких осей

Ограничение прежнего ядра устранено. `AdaptiveResearchKernelOwner.advance()` теперь перебирает discovery-only подмножества dormant-осей по мощности `1..N`, выбирает минимальную мощность, прошедшую frozen fit gate, и при необходимости активирует несколько representation-координат в одном цикле. Фиксированного числа осей на цикл нет. Sealed holdout при выборе не используется.

При этом любая такая активация остаётся исследовательской: `REPRESENTATION_ACTIVATED != CAUSALLY_ESTABLISHED`. Multi-axis birth не даёт автоматического причинного статуса ни одной из координат.

# Интеграция Collective Coordination — 0.15.29.0

Authoritative owner: `source/lawspace/collective_coordination.py`
(`COLLECTIVE-COORDINATION/1.0.0`). API surfaces:
`get_phi_collective_coordination_contract`,
`search_phi_collective_coordination_architecture`, `collective_coordination`,
`run_phi_collective_coordination_qualification`.

Поток исполнения: independent epistemic cores → typed proposals → calibrated
information value → hard resource/conflict feasibility → joint subset selection
→ typed execution. Архитектура выбирается из внутренней 576-кандидатной транши;
внешний интернет как селектор запрещён. Runtime ledger сохраняет provenance
закрытого обязательства в `resolved_architecture_obligations`.

Для воспроизведения архитектурного решения запустите
`examples/next_generation_ai_architecture_search.ipynb`. Полный журнал решений —
`docs/ARCHITECTURE_DECISION_JOURNAL.md`.

## Representation activation и причинность

В receipt адаптивного цикла эти состояния принципиально различаются:

```text
REPRESENTATION_ACTIVATED != CAUSALLY_ESTABLISHED
```

`REPRESENTATION_ACTIVATED` означает только, что residual-discovery нашёл
координату, а её добавление улучшило локальное held-out представление. Это даёт
право использовать ось как research-local predictor. Поля `causal_ready_axes`,
`causally_established_axes`, `automatic_causal_axis_selection_allowed` и
`causal_status` читаются отдельно. Пустой `causal_ready_axes` при активированной
оси является допустимым и ожидаемым fail-closed результатом, а не противоречием.

Для Navier–Stokes benchmark ожидается:

```text
representation_status = REPRESENTATION_ACTIVATED
causal_status = CAUSALLY_NOT_ESTABLISHED
causal_ready_axes = []
causally_established_axes = []
automatic_causal_axis_selection_allowed = false
```

# Primitive-field blind discovery Навье—Стокса

## Зачем нужен второй уровень

Первый benchmark получает уже вычисленные маскированные члены баланса. Второй уровень существенно строже: Atlas получает только sampled primitive fields и координатные сетки. В request отсутствуют производные, конвективные произведения, pressure-gradient coordinates, Laplacian coordinates и шаблон PDE.

До post-freeze decode поля обезличены:

```text
q0, q1, q2
f0, f1, f2, f3, f4
```

В контрольном мире post-freeze они соответствуют `t, x, y, u, v, p, rho, nu`, но эта расшифровка не передаётся ядру при поиске.

## Как рождаются операторные координаты

В существующий `TheoryCompilerKernel` добавлен один специализированный owner той функции, которой раньше не было: `PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH/1.0.0`. Он не выбирает именованный PDE. По размерностям он определяет time-like и length-like координаты, затем из sampled fields строит высокопорядковые локальные finite-difference actions и типизированные research-local operator coordinates.

Текущая безопасная grammar включает:

- первую производную поля;
- вторую пространственную производную target field;
- `field × first-derivative(target-field)`;
- `field × second-derivative(target-field)`;
- `reciprocal(field) × first-derivative(other-field)`.

Из этой grammar для каждого импульсного канала в текущем контрольном мире рождается 8 допустимых acceleration-coordinate candidates. Atlas сам выбирает discovery-only baseline и оставляет остальные dormant, после чего Adaptive Research Kernel определяет необходимую мощность multi-axis birth.

## Reference-world данные

Используются независимые sampled-field реализации нескольких режимов: периодический затухающий вихрь, жёсткое вращение, два взаимно ортогональных затухающих сдвига и два взаимно ортогональных параболических канальных режима. Discovery и sealed части имеют разные амплитуды, масштабы, вязкости, плотности и времена.

Reference fixture может знать физическую формулу для построения контрольного мира, но в `primitive_field_request` передаются только массивы координат, массивы primitive fields и их dimensions. Derived derivative values caller не передаёт.

## Запуск

Из корня patched release:

```bash
make navier-stokes-primitive-field
```

или напрямую:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python -m evaluation.navier_stokes_blind_experiment \
  --mode primitive-fields \
  --output reports/NAVIER_STOKES_PRIMITIVE_FIELD_CURRENT.json \
  --summary
```

Windows PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
python -m evaluation.navier_stokes_blind_experiment `
  --mode primitive-fields `
  --output reports/NAVIER_STOKES_PRIMITIVE_FIELD_CURRENT.json `
  --summary
```

## Ожидаемый результат текущего контрольного replay

В проверенном replay верхний статус:

```text
PASS_PRIMITIVE_FIELD_BLIND_OPERATOR_DISCOVERY
34 / 34 PASS
```

В каждом импульсном канале Atlas рождает 8 типизированных operator candidates, сам выбирает одну baseline-ось и в том же research cycle активирует ещё четыре оси (`selected_birth_cardinality = 4`). После post-freeze decode effective support соответствует пяти компонентам локального импульсного баланса: две advection coordinates, pressure-gradient/density coordinate и две diffusion coordinates.

Контрольные OOD значения текущего replay:

```text
x sealed NRMSE ≈ 3.45e-4
y sealed NRMSE ≈ 3.82e-4
```

Числа не должны трактоваться как математическое доказательство PDE: finite-difference birth вносит дискретизационную ошибку. Acceptance gate здесь `NRMSE < 1e-2`, а коэффициенты пяти post-freeze expected axes должны быть в пределах `2e-2` от `(-1,-1,-1,+1,+1)`.

## Что прислать после ручного запуска

Основной артефакт:

```text
reports/NAVIER_STOKES_PRIMITIVE_FIELD_CURRENT.json
```

Именно этот JSON содержит primitive-field birth receipt, operation signatures, baseline selection, полный adaptive multi-axis subset search, coefficients, sealed OOD evaluation, digests и provenance firewall. Его следует передавать без ручного редактирования.

## Граница утверждений

PASS второго уровня означает, что в controlled reference world Atlas получил только primitive sampled fields, сам построил допустимые локальные operator coordinates, сам выбрал multi-axis support и перенёс найденную структуру на unseen parameter holdout. Он всё ещё **не** доказывает существование/гладкость Navier—Stokes, мировой новый закон или универсальную способность открывать любой PDE. Следующий более строгий уровень должен убрать заранее заданную локальную operator grammar и заставить Mathematical Invention Kernel расширять сам набор допустимых операций при систематическом residual.

# Level 3 — рождение языка операторов до поиска PDE support

## Цель

Level 3 убирает из pre-freeze research path заранее заданную differential grammar `D`, `D^2`, `field × D(target)` и `field^-1 × D(other)`. Вместо неё `PHI-MATHEMATICAL-INVENTION-KERNEL` получает только dimensions примитивных координат/полей и более слабые meta-primitives:

- `LOCAL_TRANSLATION`;
- `LINEAR_SUPERPOSITION`;
- `POINTWISE_MULTIPLY`;
- `POINTWISE_RECIPROCAL`;
- `DIMENSION_TYPING`.

Это не «изобретение математики из ничего»: перечисленные meta-primitives являются заранее доступным вычислительным субстратом. Квалифицируется более узкое и проверяемое утверждение — Atlas способен **породить локальный операторный язык без каталога именованных differential operators**, после чего тем же adaptive kernel найти support закона.

## Механизм

Компонент `OPERATOR-LANGUAGE-BIRTH/1.0.0-COMPONENT` исследует rank-shells локальных translation responses. Ранг не передаётся как «первая» или «вторая производная». Для каждого shell строятся moment-response signatures, затем dimensions разрешают только те pointwise compositions, которые могут иметь размерность frozen target relation.

Уникальная time-like coordinate резервируется только для target action. Это предотвращает identity leakage: оператор, численно совпадающий с target time response, не может попасть в predictor language.

Текущий контрольный replay породил 20 typed signatures:

```text
rank 1: 10 signatures
rank 2:  8 signatures
rank 3:  2 signatures
rank 4:  0
rank 5:  0
```

Shell budget является только runtime guard. Receipt явно фиксирует `search_may_resume_beyond_budget=true` и `resource_budget_is_scientific_rank_ceiling=false`.

## Sparse adaptive support search

После language birth 6 из 20 operator coordinates оказались численно неидентифицируемыми на discovery data (нулевая/машинная вариация). Они сохраняются в birth receipt, но не входят в support combinatorics. Осталось 14 empirically executable candidates.

Для малых dormant spaces Atlas сохраняет exhaustive cardinality-shell search. Если полный subset count превышает trial resource budget, kernel автоматически использует:

```text
SPARSE_ADAPTIVE_FORWARD_BACKWARD_SUBSET_SEARCH
```

Forward stage наращивает support без заранее заданного cardinality, пока не пройден frozen fit gate. Backward stage удаляет лишние axes, сохраняя gate. Resource trial budget не является scientific cardinality ceiling.

В текущем replay:

```text
x lane: 20 born -> 14 identifiable -> 106 support trials -> 4 activated axes

y lane: 20 born -> 14 identifiable ->  78 support trials -> 4 activated axes
```

С baseline-осью effective support имеет 5 координат в каждом momentum lane.

## Контрольный результат

```text
PASS_BLIND_OPERATOR_LANGUAGE_INVENTION
46 / 46 PASS
```

После post-freeze decode support снова соответствует двум convective terms, pressure/density term и двум diffusion terms. Численные результаты:

```text
x discovery NRMSE ~= 2.6136e-4
x sealed    NRMSE ~= 3.4519e-4

y discovery NRMSE ~= 3.0600e-4
y sealed    NRMSE ~= 3.8246e-4
```

Коэффициенты пяти выбранных членов находятся около `(-1,-1,-1,+1,+1)` с отклонениями порядка `1e-4`.

## Запуск

```bash
make navier-stokes-operator-language
```

или:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python -m evaluation.navier_stokes_blind_experiment \
  --mode invented-language \
  --output reports/NAVIER_STOKES_OPERATOR_LANGUAGE_INVENTION_CURRENT.json \
  --summary
```

Полный journal находится в том же JSON в `run_journal`, а Jupyter replay — в `examples/navier_stokes_blind_experiment.ipynb`.

## Claim boundary

Level-3 PASS не устанавливает новый физический закон, причинность выбранных axes, мировую математическую новизну или «изобретение дифференциального исчисления из ничего». Он квалифицирует более сильный механизм, чем Level 2:

```text
primitive sampled fields
-> weak translation/algebra meta-primitives
-> Atlas-generated operator language
-> data-driven identifiability screen
-> adaptive sparse multi-axis support search
-> sealed OOD verification
```

`REPRESENTATION_ACTIVATED` отдельно от `CAUSALLY_ESTABLISHED`; в текущем receipt causal status остаётся `CAUSALLY_NOT_ESTABLISHED`.

# Level 4 — residual-driven discovery неизвестного члена

## Цель

Level 4 проверяет уже не восстановление известной PDE-структуры, а более строгий исследовательский цикл: текущая representation намеренно неполна, frozen baseline известен, а дополнительный член отсутствует в начальном generated language. Atlas должен сам зафиксировать persistent residual, открыть следующий algebra-depth shell, породить новые typed operator coordinates и проверить найденный кандидат на sealed OOD.

Контрольный world не является заявлением о новой физике. Он специально сконструирован так, чтобы post-freeze известный дополнительный член требовал двух pointwise carrier factors, тогда как initial language разрешает только один. Поисковое ядро не получает ни semantic name этого члена, ни его coefficient, ни его operator signature.

## Residual-driven algebra expansion

`OPERATOR-LANGUAGE-BIRTH` теперь поддерживает pointwise monomial carrier depth как открываемый resource shell. При depth `1` сохраняется Level-3 язык. Если frozen discovery fit gate не достигнут, `ADAPTIVE-RESEARCH-KERNEL` запускает следующий shell с depth `2`, затем при необходимости может продолжить дальше в пределах текущего runtime budget.

Budget не является scientific ceiling:

```text
carrier_factor_budget_is_scientific_ceiling = false
language_expansion_triggered_only_by_persistent_discovery_residual = true
sealed_holdout_used_to_trigger_language_expansion = false
```

Для carrier exponent vector `s=(s_1,...,s_m)` Atlas строит композиции

```text
product_j f_j^(s_j) * L_r[g]
```

только если dimensional typing допускает frozen target dimension. Противоположные factors, взаимно сокращающиеся до shallower shell, не считаются новым birth.

## Контрольный Level-4 result

Начальный frozen baseline использовал одну Atlas-born operator coordinate. При carrier depth `1` система породила только 4 typed signatures и не прошла fit gate:

```text
initial discovery NRMSE = 5.555687904876772e-1
status = REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES
```

Persistent residual автоматически открыл carrier depth `2`. Новый shell дал 26 typed signatures. Adaptive support search оставил ровно baseline + одну новую coordinate. После post-freeze decode новый член соответствует скрытой двухфакторной composition, а коэффициенты равны:

```text
baseline coefficient = -0.9999999999998731
hidden candidate      = -0.6499999999999957
reference lambda      =  0.65
```

Ошибка после discovery:

```text
final discovery NRMSE = 1.5146444163333484e-13
sealed OOD NRMSE      = 1.5289221198455143e-13
sealed record count   = 156
```

Acceptance:

```text
PASS_BLIND_HIDDEN_TERM_DISCOVERY
19 / 19 PASS
TOP_LEVEL_ATLAS_PROVENANCE_ACCEPTED = PASS
```

## Верхняя provenance-печать Level 4

Успешная численная подгонка сама по себе больше не достаточна для PASS этого контроля. `execution_receipt` обязан содержать `owner`, `schema`, `input_digest`, `axis_registry_digest`, `hypothesis_space_digest`, `code_digest`, `result_digest` и итоговый `digest`. `CLAIM-PROVENANCE-FIREWALL` пересчитывает цепочку и выдаёт `ATLAS_NATIVE_PROVENANCE_ACCEPTED_NOT_SCIENTIFIC_PROMOTION` только при её целостности.

Проверить поля можно так:

```bash
python - <<'PY'
import json
r = json.load(open('reports/HIDDEN_TERM_RESIDUAL_DISCOVERY_CURRENT.json'))['execution_receipt']
print(r['atlas_claim']['status'])
print(r['atlas_claim']['checks'])
PY
```

Ожидаются `atlas_native = true`, `required_receipt_fields_present = true`, `code_digest_bound = true`, `result_digest_bound = true` и `receipt_digest_valid = true`. Эта печать удостоверяет происхождение выполнения, но не превращает representation coordinate в причинно установленную переменную и не продвигает гипотезу в научный закон.

## Запуск

```bash
make hidden-term-discovery
```

или напрямую:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
python -m evaluation.navier_stokes_blind_experiment \
  --mode hidden-term \
  --output reports/HIDDEN_TERM_RESIDUAL_DISCOVERY_CURRENT.json \
  --summary
```

## Claim boundary

Level-4 PASS означает только следующее: на controlled reference world Atlas смог обнаружить, что текущий representation language недостаточен, расширить его из уже разрешённых meta-primitives, выбрать новую typed composition и перенести найденную correction на unseen sealed parameters. Это **не** доказывает, что найден мировой новый закон, и не устанавливает причинность. `CAUSALLY_NOT_ESTABLISHED` сохраняется.

# Blind DNS turbulence-closure experiment

Эксперимент принимает периодические равномерные DNS snapshots с трёхмерными массивами `u`, `v`, `w`. Адаптер применяет frozen spectral low-pass и вычисляет exact unresolved convective forcing как разность между отфильтрованной нелинейной динамикой DNS и нелинейной динамикой resolved-поля. Это аттестованный target, а не переданная closure-гипотеза.

В режиме `DIRECT_FIELD_VALUE` размерность response берётся непосредственно из target-field, а target исключается из `predictor_fields`. Mathematical Invention рождает размерностно допустимые координаты только из resolved velocity и filter-width полей; Theory Compiler вычисляет локальные translation-moment responses. Ресурсные rank/depth budgets ограничивают запуск, но не объявляют научный потолок языка.

Полная инструкция находится в [RUN_TURBULENCE_DNS_CLOSURE_RU.md](RUN_TURBULENCE_DNS_CLOSURE_RU.md). Базовый запуск:

```bash
make turbulence-dns-closure \
  DNS_MANIFEST=examples/turbulence_dns_closure_manifest.local.json
```

Допустимые научные исходы: переносимый кандидат, fit без прохождения null-control либо representation gap/transfer failure. Ни один из них автоматически не устанавливает причинность или новый закон.

### Новые тесты DNS/direct-target

- `tests/test_direct_target_residual_discovery.py::test_direct_target_field_is_excluded_and_recovered` — строит прямое residual-field отношение, проверяет исключение target из всех predictor signatures, точное восстановление коэффициента и sealed OOD без научного продвижения.
- `tests/test_turbulence_dns_closure_experiment.py::test_sgs_residual_is_finite_and_nontrivial` — генерирует периодический 3D snapshot, применяет DNS adapter и проверяет конечность, размерность массивов и ненулевой coarse-graining residual.
- `tests/test_turbulence_dns_closure_experiment.py::test_dns_closure_harness_completes_without_auto_promotion` — запускает полный discovery/sealed harness на controlled 3D данных. Ожидается `PASS_PROTOCOL_INTEGRITY`, непересекающиеся regimes, валидная Atlas provenance и `scientific_law_established=false`.
