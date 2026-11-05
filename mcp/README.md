# Права через MCP

Опасный ресурс агент получает только через MCP-сервер, который знает, что запрещено. Права задаются набором инструментов: чего нет в сервере, того агент сделать не может.

| Сервер (соло-этап) | Запрещает |
|---|---|
| test-env-broker | подключение к тестовой БД в обход резервации |
| ast-mutator | текстовую запись кода; файлы Red Zone — только просмотр |
| spec-registry | PR без привязки к спецификации |
| semgrep-gate | коммит без проверки качества |
| context-freshness | генерацию на устаревшем контексте |
| call-transcript | доступ к персональным данным без маскирования |

Пример — `test_env_broker.py`: аренда тестовой среды с TTL, heartbeat и очередью. Это прообраз Resource Reservation Manager: в соло-режиме один сервер, на команде — аренда задач (`SKIP LOCKED`), heartbeat, сборщик зависших и семафор провайдера.

Запуск (нужен пакет `mcp`):

```bash
pip install "mcp>=1.2"
python mcp/test_env_broker.py
```

Подключение в Claude Code — `.mcp.json` в корне проекта:

```json
{ "mcpServers": { "test-env-broker": { "command": "python", "args": ["mcp/test_env_broker.py"] } } }
```

Список сред — переменная `TEST_ENVS` (по умолчанию `test-db-1,test-db-2`), состояние — файл `BROKER_STATE`.
