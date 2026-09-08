# Подключение новой науки

`data/domains/*.json` — единственная декларативная точка регистрации предметных осей новой науки.

Обязательный минимум manifest:

- `schema = phi-domain-plugin-manifest/v1`;
- уникальный `domain_id`;
- `common_rules_owner = COMMON-SCIENTIFIC-RULES/1.0.0`;
- список domain-specific `axes`;
- необязательный `owner.module` + `owner.class`, если науке нужны собственные уравнения, совместимость, семантические преобразования или experiment models.

В domain manifest **запрещено копировать** общие правила evidence/verification/novelty/EIG/scientific promotion. Они маршрутизируются через `source/lawspace/scientific_rules.py` к единственным authoritative owners.

Добавление manifest не требует изменения `source/lawspace/domains.py`. После изменения manifest требуется новый запуск процесса/импорт registry, чтобы frozen runtime не менял пространство осей на лету.
