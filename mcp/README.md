# 10 MCP-серверов: права на уровне инструментов

Опасный ресурс агент получает только через MCP-сервер, который знает, что запрещено. Права задаются набором инструментов: чего нет в сервере, того агент сделать не может.

Это обобщённые версии 10 серверов соло-этапа. Оригиналы были написаны под SIP-платформу (RTP-ядро, сценарии диалогов, расшифровки звонков); здесь — те же паттерны для любого проекта. В скобках — имя на соло-этапе.

| Сервер | Инструменты | Запрещает | Настройка |
|---|---|---|---|
| `test-env-broker` | `reserve_test_env`, `renew_test_env`, `release_test_env`, `queue_position` | подключение к общей тестовой БД без аренды | `TEST_ENVS=test-db:2` |
| `safe-edit` (ast-mutator) | `is_red_zone_file`, `preview_diff`, `apply_edit` | запись в Red Zone и за пределы репозитория, в том числе через симлинки | `HARNESS_RED_ZONE` |
| `spec-registry` | `list_specs`, `get_spec`, `can_create_pr` | MR, в котором коммиты без строки `Spec:` или `ADR:` | `SPEC_DIRS` |
| `quality-gate` (semgrep-gate) | `run_quality_gate`, `get_violation_report` | коммит без проверки; агент получает итог, а не весь лог | — |
| `context-freshness` | `get_repo_snapshot_hash`, `is_context_fresh`, `refresh_context` | план и правки на устаревшей копии репозитория | `FRESH_REF=origin/dev`, `FRESH_FETCH=1` |
| `pii-reader` (call-transcript) | `read_masked`, `search_masked` | чтение email, телефонов, номеров карт и IBAN без масок | `PII_ROOT=data` |
| `schema-store` (dialog-scenario-store) | `get_doc`, `propose_patch`, `apply_patch` | правку JSON, которая ломает его JSON Schema | `SCHEMA_MAP=папка:схема` |
| `readonly-view` (rtp-core-readonly) | `list_files`, `read_file` | любую запись в ядро: у сервера нет пишущих инструментов | `READONLY_ROOT=core` |
| `slot-scheduler` (gpu-scheduler) | `request_slot`, `renew_slot`, `release_slot`, `query_queue_position` | GPU, слот провайдера LLM или лицензию без аренды | `SLOTS=gpu:2,llm:8` |
| `redteam-runner` (adversarial-runner) | `list_scenarios`, `run_scenario`, `run_all` | ничего — атакует 27 барьеров на временном репозитории | `HARNESS_KIT` |

`test-env-broker` и `slot-scheduler` — это и есть Resource Reservation Manager в миниатюре: аренда с TTL, heartbeat (`renew_*`), очередь FIFO и автоматический возврат просроченных аренд.

## Установка

`./harness.sh install <repo>` копирует серверы в `<repo>/.harness/mcp/` и создаёт `<repo>/.mcp.json` (формат Claude Code) со всеми десятью. Дальше:

```bash
pip install -r .harness/mcp/requirements.txt
```

Подключение в OpenCode — раздел `mcp` в `opencode.json`:

```json
{ "mcp": { "safe-edit": { "type": "local", "command": ["python", ".harness/mcp/safe_edit.py"], "enabled": true } } }
```

Серверы работают с `mcp` 1.x (`FastMCP`) и 2.x (`MCPServer`) — импорт выбирается автоматически в `servers/_common.py`. Состояние аренд — в `.harness/state/` (в `.gitignore`).

## Проверка

```bash
pip install -r mcp/requirements.txt
python mcp/selftest.py
```

Self-test для каждого сервера:
1. поднимает его по stdio и делает `initialize` + `tools/list` по протоколу MCP;
2. вызывает инструменты на временном репозитории и проверяет поведение: аренда и очередь, отказ в Red Zone и за пределами репозитория, маски для персональных данных, отказ невалидному JSON, 27 атак `redteam-runner`.

CI прогоняет self-test на `mcp<2` и `mcp>=2`.
