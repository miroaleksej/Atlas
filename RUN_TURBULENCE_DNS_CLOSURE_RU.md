# Запуск blind DNS turbulence-closure experiment

Этот эксперимент предназначен для **реальных periodic DNS snapshots**. Он не содержит заранее выбранной turbulence-closure модели и не гарантирует научный `PASS`: `REPRESENTATION_GAP_OR_TRANSFER_FAILURE` является допустимым результатом.

## 1. Подготовьте DNS snapshots

Каждый файл `.npz` должен содержать:

- `u`, `v`, `w` — три конечных 3D массива одинаковой формы;
- либо один scalar `dx` для изотропной равномерной сетки;
- либо scalar `dx`, `dy`, `dz`;
- либо 1D arrays `x`, `y`, `z`.

Минимальный пример сохранения уже имеющихся NumPy-массивов:

```python
import numpy as np
np.savez_compressed("dns_snapshot.npz", u=u, v=v, w=w, dx=dx)
```

Текущий adapter использует spectral low-pass и поэтому предполагает periodic uniform DNS.

## 2. Создайте manifest

Скопируйте:

`examples/turbulence_dns_closure_manifest.template.json`

в, например:

`examples/turbulence_dns_closure_manifest.local.json`

и замените `path` на реальные файлы. Discovery и sealed наборы должны иметь **разные `regime_id`**. Для настоящего transfer-test желательно, чтобы это были разные Reynolds number, forcing regime или другой flow regime.

Также шаблон можно сгенерировать командой:

```bash
python -m evaluation.turbulence_dns_closure_experiment \
  --write-manifest-template examples/turbulence_dns_closure_manifest.local.json
```

## 3. Запустите

Первый полный запуск:

```bash
python -m evaluation.turbulence_dns_closure_experiment \
  --manifest examples/turbulence_dns_closure_manifest.local.json \
  --components x,y,z \
  --output reports/TURBULENCE_DNS_CLOSURE_CURRENT.json \
  --summary
```

Или:

```bash
make turbulence-dns-closure DNS_MANIFEST=examples/turbulence_dns_closure_manifest.local.json
```

Null-control включён по умолчанию. Для диагностического быстрого запуска его можно временно отключить `--skip-null-control`, но такой запуск слабее как научное свидетельство.

## 4. Что прислать обратно

Пришлите один файл:

`reports/TURBULENCE_DNS_CLOSURE_CURRENT.json`

Ключевые поля:

- `protocol_status` — корректность blind/freeze/provenance протокола;
- `component_outcomes` — научный результат по x/y/z;
- `components[*].summary.selected_axes` — Atlas-born operator coordinates;
- `real_sealed_nrmse` — transfer error;
- `null_sealed_nrmse` — negative-control error;
- `atlas_native` — provenance;
- `claim_boundary` — запрет автоматического объявления закона.

Возможные научные исходы:

- `TRANSFER_CANDIDATE_SURVIVES_CURRENT_SEALED_AND_NULL_EVIDENCE_NOT_LAW`;
- `TRANSFER_FIT_SURVIVES_BUT_NULL_CONTROL_NOT_REJECTED`;
- `REPRESENTATION_GAP_OR_TRANSFER_FAILURE`.

Даже первый статус означает только сильного кандидата для дальнейшей независимой фальсификации, а не новый закон турбулентности.
