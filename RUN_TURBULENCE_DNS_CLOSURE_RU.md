# Реальный blind DNS turbulence-closure experiment (JHTDB)

Этот комплект предназначен для **реального** эксперимента на Johns Hopkins Turbulence Database. Synthetic snapshots для научного запуска не используются.

## Что зафиксировано до запуска Atlas

Discovery и sealed данные выбраны заранее и записаны в `examples/JHTDB_REAL_DNS_DOWNLOAD_PLAN.json`.

- **DISCOVERY**: 4 независимых cutout из `isotropic1024coarse`, DNS 1024³, Taylor-scale Reynolds number примерно `R_lambda ~ 433`.
- **SEALED_HOLDOUT**: 2 пространственно разнесённых cutout из отдельного `isotropic4096`, DNS 4096³, `R_lambda = 610.57`.
- source cube: `18×18×18` grid points;
- spectral coarse-graining in Atlas: `filter_ratio = 2`;
- Atlas grid after coarse-graining: `9×9×9`;
- только raw velocity `u,v,w` загружается из JHTDB;
- derivative/closure predictors из JHTDB не загружаются;
- известная LES/RANS closure модель Atlas не передаётся.

Таким образом sealed часть отличается не только пространственной областью, но и Reynolds regime / DNS resolution.

## 1. Скачать реальные DNS snapshots

Никаких `.npz` вручную создавать не нужно. Выполните из корня Atlas:

```bash
python -m evaluation.fetch_jhtdb_real_snapshots
```

Downloader использует официальный JHTDB REST `getCutout`. По умолчанию применяется публичный testing token JHTDB. Каждый запрос содержит 2916 grid points, то есть остаётся ниже публичного лимита `<4096`, и запросы выполняются **последовательно**, не параллельно.

Если у вас есть собственный JHTDB token:

Windows PowerShell:

```powershell
$env:JHTDB_TOKEN="ВАШ_TOKEN"
python -m evaluation.fetch_jhtdb_real_snapshots
```

Linux/macOS:

```bash
export JHTDB_TOKEN="ВАШ_TOKEN"
python -m evaluation.fetch_jhtdb_real_snapshots
```

После успешной загрузки появятся:

```text
examples/dns_snapshots/
    dns_discovery_01.npz
    dns_discovery_02.npz
    dns_discovery_03.npz
    dns_discovery_04.npz
    dns_sealed_01.npz
    dns_sealed_02.npz
    JHTDB_DOWNLOAD_PROVENANCE.json

examples/turbulence_dns_closure_manifest.real.json
```

Каждый `.npz` содержит:

- `u`, `v`, `w` — реальные JHTDB velocity arrays формы `18×18×18`;
- `dx` — реальный grid spacing соответствующего DNS.

`JHTDB_DOWNLOAD_PROVENANCE.json` фиксирует исходный dataset, time index, 1-based grid coordinates, REST request metadata, response SHA-256 и SHA-256 каждого итогового `.npz`. Private token в receipt не записывается.

Для просмотра frozen download plan без сети:

```bash
python -m evaluation.fetch_jhtdb_real_snapshots --dry-run
```

## 2. Запустить Atlas

После получения шести `.npz`:

```bash
python -m evaluation.turbulence_dns_closure_experiment \
  --manifest examples/turbulence_dns_closure_manifest.real.json \
  --components x,y,z \
  --output reports/TURBULENCE_DNS_CLOSURE_CURRENT.json \
  --summary
```

Самый простой вариант — одна Python-команда, работающая и в Windows PowerShell:

```bash
python -m evaluation.run_real_jhtdb_dns_closure
```

Она сначала скачает и SHA-256-зафиксирует реальные JHTDB `.npz` (если их ещё нет), затем запустит Atlas.

Если `make` доступен, эквивалентно:

```bash
make turbulence-dns-closure-real
```

Эта цель скачает реальные JHTDB snapshots только если готового real manifest ещё нет, затем запустит Atlas.

## 3. Что именно проверяется

DNS adapter вычисляет наблюдаемый coarse-graining residual

`target_i = -( filter(u_j * d_j u_i) - U_j * d_j U_i )`,

где `U` — frozen spectral low-pass velocity. Это **target**, а не подсказанная closure модель.

Atlas получает masked resolved velocity fields, filter width и target. Производные и operator coordinates должны возникнуть внутри Atlas. Sealed `isotropic4096` не используется для axis birth.

Null-control включён по умолчанию.

## 4. Честные возможные исходы

- `TRANSFER_CANDIDATE_SURVIVES_CURRENT_SEALED_AND_NULL_EVIDENCE_NOT_LAW` — найден переносимый кандидат, но это ещё не закон;
- `TRANSFER_FIT_SURVIVES_BUT_NULL_CONTROL_NOT_REJECTED` — fit есть, но отрицательный контроль не отделён;
- `REPRESENTATION_GAP_OR_TRANSFER_FAILURE` — текущего языка Atlas недостаточно или перенос не подтверждён.

Последний исход не является ошибкой программы: это исследовательский результат.

## 5. Что прислать обратно

После запуска пришлите:

`reports/TURBULENCE_DNS_CLOSURE_CURRENT.json`

Желательно также сохранить:

`examples/dns_snapshots/JHTDB_DOWNLOAD_PROVENANCE.json`

по нему можно независимо проверить, какие реальные JHTDB данные вошли в experiment freeze.
