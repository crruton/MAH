# Extras

Модули, которые **не ставятся по умолчанию**. У каждого есть цена в каждой сессии агента, а польза — только в части проектов. Подключайте модуль, когда статистика ошибок (`./harness.sh errors`) показала проблему, которую он закрывает, и проверяйте цену (`./harness.sh budget --repo <repo>`).

## MCP-серверы — `mcp/`

10 серверов: аренда тестовых сред, слоты GPU/LLM, безопасная правка с Red Zone, реестр спек, маски персональных данных, правка JSON по схеме, чтение ядра без записи, красная команда для барьеров. Описание каждого — [mcp/README.md](mcp/README.md).

Описания инструментов сервера лежат в контексте **каждой** сессии: 120–380 токенов на сервер, все десять — ~2 300. Лишние инструменты ещё и путают агента при выборе. Подключайте только серверы для ресурсов, которые реально есть в проекте:

```bash
mkdir -p <repo>/.harness/mcp
cp extras/mcp/servers/_common.py extras/mcp/servers/test_env_broker.py <repo>/.harness/mcp/
pip install -r extras/mcp/requirements.txt
```

Затем в `<repo>/.mcp.json` — только нужные записи из [mcp/mcp.json](mcp/mcp.json). Проверка: `python extras/mcp/selftest.py`.

## Доменные скиллы — `skills/`

10 скиллов соло-этапа (SIP-платформа), обобщённые: `async-boundary`, `test-isolation`, `spec-first-diff`, `latency-budget`, `secrets-guard`, `schema-first-config`, `flaky-statistics`, `context-freshness`, `invariants-guard`, `red-team-scenarios`. Описание скилла — ~30 токенов в каждой сессии; тело — только при использовании. Ставьте те, что совпадают с вашим стеком:

```bash
cp -r extras/skills/async-boundary ~/.claude/skills/
```

## Гейт `check-large-files`

Для репозиториев, куда случайно попадают дампы и бинарники: `HARNESS_EXTRA="check-large-files" bash gates/run-all.sh`. Порог — `HARNESS_MAX_FILE_KB` (1024).

## Нагрузочный тест — `loadtest/`

Шаблон k6 со ступенями до целевого RPS. Только для изолированного стенда. См. [loadtest/README.md](loadtest/README.md).
