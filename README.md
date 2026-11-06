# self-harness

Лёгкий харнес для ИИ-агентов разработки. Ставится **один раз на машину** и работает во всех проектах: в репозитории ничего не копируется. Ловит действия, после которых работу не вернуть, считает ошибки агентов по всем проектам и показывает, сколько стоит сам.

*A lightweight, project-independent harness for AI coding agents (Claude Code). One global install: a guard hook (deny only what git cannot bring back, ask for the rest, allow everything else), an error collector with cross-project statistics, a learning dashboard, 5 process skills. ~160 tokens per session, ~110 ms per tool call. Optional CI gates for teams. Docs are in Russian. MIT.*

```bash
git clone https://github.com/crruton/self-harness.git
cd self-harness
./harness.sh install      # Windows: harness.cmd install  (нужен Git for Windows и jq)
./harness.sh demo         # 35 атак должны остановиться, 16 обычных действий — пройти
```

Удалить: `./harness.sh uninstall`. Ваши настройки, хуки и скиллы остаются как были.

---

## Что ставится

| Что | Куда | Стоимость |
|---|---|---|
| `guard.sh` — барьеры B04–B06, B28–B33 | `~/.claude/harness/hooks/`, запись PreToolUse в `settings.json` | ~70 мс на вызов инструмента |
| `collect-tool-errors.sh` — сборщик упавших вызовов | запись PostToolUse (выключить: `--no-tool-errors`) | ~40 мс на вызов, `jq` только при ошибке |
| 5 процессных скиллов | `~/.claude/skills/` | ~160 токенов в сессии (только описания) |
| Хранилище и статистика ошибок | `~/.claude/harness/errors/`, `bin/` | 0 |
| Глобальные правила (`--rules`) | импорт в `~/.claude/CLAUDE.md` | ~600 токенов; по умолчанию **не ставятся** — у вас могут быть свои |

Установщик дописывает в `~/.claude/settings.json` две записи и делает резервную копию. Чужие хуки и ключи не трогает, повторный запуск ничего не дублирует, `uninstall` возвращает файл в исходное состояние. Скилл с тем же именем, который уже есть у вас, остаётся вашим.

Свой замер: `./harness.sh budget`.

## guard.sh: запретить, спросить, пропустить

Каждая блокировка — лишний вопрос человеку. Поэтому запрет только для того, что git не вернёт.

| Уровень | Что | Почему |
|---|---|---|
| **Запретить** | B05: `git reset --hard`, `git clean -f`, `git checkout -- .`, `git restore .`, force-push (в том числе `--force-with-lease`), удаление ветки на сервере, `rm -rf` для `/`, `~`, `$HOME`, `.`, `..`, `*`, `.git`; B06: чтение и правка `.env`, ключей, сертификатов, `secrets/`; B28: `--no-verify`, `HUSKY=0`; B31: хранилища токенов (`~/.aws/credentials`, `~/.kube/config`, `~/.docker/config.json`, `.git-credentials`, `.netrc`, `~/.ssh/id_*`); B32: ручная правка lock-файлов и `node_modules/`, `.venv/` | теряется незакоммиченная работа или чужая история; хук нашёл проблему, а агент её обходит; секреты не должны попадать в контекст модели; lock-файл расходится со сборкой |
| **Спросить** | B04: полный прогон тестов (npm, pytest, go, cargo, maven, gradle, dotnet, rspec, phpunit, mix, swift, flutter, deno, ctest, make test); B05: `git branch -D`, `DROP`/`TRUNCATE`, `docker system/volume prune`; B29: `curl … \| sh`; B30: `npm publish`, `docker push`, `terraform apply`, `kubectl delete`, `helm upgrade`, деплой; B31: `env`, `printenv`, `echo $…TOKEN`; B33: правка хуков и настроек агента | бывает нужно, но действие уходит за пределы машины, открывает секреты или меняет защиту самого агента |
| **Пропустить** | всё остальное: `rm -rf build`, `docker compose down -v`, `git push origin dev`, `git push -n`, тесты пакета, `terraform plan`, `curl … \| jq`, `printenv PATH`, `.env.example`, `*.pub` | обычная работа |

Проверки видят команду и внутри обёрток: `sh -c '…'`, `bash -c`, `python -c`. «Спросить» — это ответ хука `permissionDecision: "ask"` в Claude Code: агент не упирается в стену, человек решает одним нажатием. Полный прогон тестов без вопроса: `CLAUDE_FULL_TESTS=1 <команда>`.

Демо проверяет обе стороны: 35 атак должны остановиться и 16 обычных действий должны пройти без вопроса. Ложное срабатывание проваливает демо так же, как пропущенная атака.

## Сборщик и статистика ошибок

Каждое событие — строка JSON в `~/.claude/harness/errors/events-ГГГГ-ММ-<автор>.jsonl`: какой барьер, что заблокировано или о чём спросили, агент или человек, в каком репозитории. Секреты и персональные данные маскируются до записи. Сборщик никогда не роняет хук.

| Источник | Что попадает |
|---|---|
| `hook` | заблокированное или спрошенное действие агента (B04–B06, B28–B33) |
| `tool` | упавший вызов инструмента агента: команда и ошибка |
| `git-hook`, `gate` | срабатывания git-хуков и гейтов CI (проектный режим) |
| `manual` | инцидент `./harness.sh incident` |

```bash
./harness.sh errors                    # все проекты
./harness.sh errors --project shop     # один проект
./harness.sh errors --suggest          # повторы → готовые команды incident
```

| В отчёте | Что делать |
|---|---|
| **Блоки** по барьерам | каждый блок — ошибка, которая не дошла до кода |
| **Вопросы человеку** | барьер часто спрашивает, а вы всегда разрешаете — ложное срабатывание, его надо ослабить |
| По проектам и неделям | где и когда агент ошибается чаще |
| Повторы за 7 дней | барьер держит, но агента туда ведёт инструкция — исправьте источник |
| Инциденты по уровню барьера | много «текст» — правила не проверяются машиной |

Пример — ошибки агента, который собирал этот репозиторий: [error.md](error.md) и [docs/errors.md](docs/errors.md).

## Петля самосовершенствования и дашборд

Модель между сессиями не учится, учится среда. Ошибка проходит шесть шагов: поймать → заметить → записать в `error.md` → запретить барьером с атакой-репро в демо → научить (сообщение барьера и строка правила) → проверить. Подробно — [docs/LOOP.md](docs/LOOP.md).

```bash
./harness.sh dashboard     # ~/.claude/harness/dashboard.html
```

Дашборд отвечает на вопрос «агент становится лучше?» цифрами за последние 4 недели против 4 предыдущих: ошибки инструментов и попытки запрещённого на 100 вызовов, токены, USD и активное время на сессию, вопросы человеку. Для каждого инцидента — что стало после барьера: «агент не пытается», «барьер держит, агент пытается» или «утечка». Отдельно — ошибки, остановленные до первого инцидента, новые варианты, которые барьеры поймали без подсказки, и кандидаты в следующие барьеры. Знаменатель берётся из журналов сессий Claude Code, поэтому хуки на успешных вызовах ничего не стоят.

## 5 скиллов

Только процессные — они полезны в любом проекте. Тексты на английском по [ASD-STE100](docs/STE.md): короче и однозначнее.

| Скилл | Когда агент его берёт |
|---|---|
| [`error-to-rule`](skills/error-to-rule/SKILL.md) | после ошибки: запись в `error.md`, барьер, репро-тест |
| [`adr-decision`](skills/adr-decision/SKILL.md) | перед планом и при архитектурном решении |
| [`harness-review`](skills/harness-review/SKILL.md) | при изменении правил, хуков, гейтов (методы из harness2) |
| [`ste-writing`](skills/ste-writing/SKILL.md) | когда пишет текст, который читают агенты |
| [`change-pipeline`](skills/change-pipeline/SKILL.md) | перед коммитом и push |

## Проектный режим (по желанию)

Для команды, которой нужны проверки в CI. Глобальная установка для него не нужна.

```bash
./harness.sh project <repo> [--team-store] [--lock]
```

Ставит `.githooks/` (B01–B03), `gates/` (17 гейтов), `error.md`, каталог ADR, шаблон MR. `--team-store` — общее хранилище ошибок `.harness/errors/` в репозитории (файл на автора и месяц, сливается в git без конфликтов). `--lock` — `harness.lock`: правка хуков и гейтов не пройдёт CI без ревью.

| ID | Барьер | Что ловит |
|---|---|---|
| B01–B02 | `pre-push` | push в `main`, force-push, удаление ветки |
| B03 | `commit-msg` | «wip», «fix», слишком короткие и длинные заголовки |
| B07 | `check-secrets` | ключи AWS/GitHub/GitLab/Slack, JWT, приватные ключи, пароли в коде |
| B08 | `check-forbidden-files` | `.env`, `*.pem`, `id_rsa` в git |
| B10 | `check-conflict-markers` | забытые `<<<<<<<` |
| B11 | `check-test-weakening` | добавлен `skip`/`.only`/`#[ignore]`, удалены assert |
| B34 | `check-test-deletion` | удалён тестовый файл или тест-функция |
| B35 | `check-suppressions` | новый `eslint-disable`, `@ts-ignore`, `# noqa`, `//nolint`, `#[allow]`… без причины на той же строке |
| B36 | `check-leftovers` | `// ... rest of the code unchanged` вместо кода, `todo!()`, `debugger`, `pdb.set_trace()`, `binding.pry` |
| B37 | `check-lockfile-sync` | в манифесте изменились зависимости, а lock-файл нет (npm, yarn, pnpm, poetry, uv, cargo, go, bundler, composer, mix, pub) |
| B13–B15 | `check-adr-*` | дубли номеров, пустые поля, ссылки на несуществующие ADR |
| B16 | `check-error-log` | инцидент закрыт без барьера и репро-теста |
| B17 | `check-rules-size` | AGENTS.md длиннее 150 строк |
| B18 | `check-ste` | правило для агента нарушает ASD-STE100 |
| B19 | `check-zones` | настройки проекта разрешают Red Zone или отключают хуки |
| B20 | `check-harness-integrity` | хук или гейт изменён без ревью (с `--lock`) |
| B21–B27 | `check-portability` | ошибки Linux → Windows: `re.M`+`\s`, голый `bash` в subprocess, `communicate()` с JSON-RPC, зависимость без верхней границы, текст без `encoding=`/`newline=`, CRLF, нет бита исполнения |

Гейты проверяют только изменение (`HARNESS_BASE` в CI), без внешних зависимостей. Нет ADR, `error.md` или `harness.lock` — соответствующий гейт ничего не делает. Подключение: [`ci/`](ci/). Подробно о каждом гейте — в `gates/*.py`.

**B21–B27 — ошибки агента, который собирал этот репозиторий**, раз за разом при переходе между Linux и Windows. Каждая записана в [error.md](error.md); ошибка B21 повторилась дважды, потому что первое исправление не стало барьером.

## Extras

Не ставятся по умолчанию: у каждого модуля есть цена, а польза — только в части проектов. См. [extras/README.md](extras/README.md).

| Модуль | Когда нужен | Цена |
|---|---|---|
| 10 MCP-серверов (аренда тестовых сред, слоты GPU/LLM, маски PII, безопасная правка…) | в проекте есть такой общий ресурс | 120–380 токенов на сервер в каждой сессии |
| 10 доменных скиллов (async-boundary, latency-budget, invariants-guard…) | стек совпадает | ~30 токенов на скилл |
| `check-large-files` | репозиторий с бинарниками | `HARNESS_EXTRA="check-large-files"` |
| Нагрузочный тест k6 | сервис под нагрузкой | 0 |

## Окупается ли харнес

Харнес полезен, только если его цена меньше цены ошибок, которые он ловит. Раз в неделю: `./harness.sh budget` против `./harness.sh errors`. Барьер, который за месяц ни разу не сработал, но стоит токенов или миллисекунд, — кандидат на удаление; барьер, который часто спрашивает, а вы всегда разрешаете, — кандидат на ослабление.

Как это нашлось на самом наборе: первая версия хуков стоила ~2,5 с на каждый вызов инструмента, профиль со всеми MCP и скиллами — ~3 000 токенов в сессии, `guard-destructive` блокировал `docker compose down -v` и `rm -rf build`. Сейчас — ~110 мс, ~160 токенов, 0 ложных срабатываний в демо.

## Процесс

Пак — инструмент для процесса из 6 шагов: базовая линия → ошибка → правило → командные границы → пайплайн проверок → замеры → фиксация. Подробно — [PROCESS.md](PROCESS.md). Ревью правок харнеса — [review/](review/).

## Команды

```
./harness.sh                       меню
./harness.sh install [--rules] [--no-tool-errors]
./harness.sh uninstall [--purge]
./harness.sh demo [Bnn]
./harness.sh errors [--project NAME] [--suggest]
./harness.sh budget [--repo PATH]
./harness.sh dashboard [--repo PATH] [--json]
./harness.sh doctor
./harness.sh project <repo> [--team-store] [--lock]
./harness.sh check | lock | metrics <repo>
./harness.sh incident <repo> "что случилось"
./harness.sh adr <repo> "решение"
```

Папка настроек — `CLAUDE_CONFIG_DIR`, иначе `~/.claude`. Требования: git, bash, Python 3.10+, jq (без `jq` хук ничего не блокирует).

## Откуда это

Доклад «Харнес, который написал сам себя», HighLoad++ 2026, Андрей Носов. Соло-этап на SIP-платформе (10 скиллов, 10 MCP — теперь в `extras/`), командный этап на ArcSpace (5 инженеров, 37 ролей агентов, 18 недель: доля коммитов-исправлений ~50% → < 5%).

## Лицензия

[MIT](LICENSE)
