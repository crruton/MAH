# self-harness

Процесс, в котором ИИ-агенты работают над проектом и сами держат границы его дрейфа. Здесь всё, чтобы взять этот процесс, развернуть у себя одной командой и попробовать: **27 барьеров, сборщик и статистика ошибок, 15 скиллов, 10 MCP-серверов, 16 гейтов для CI**, профили с замером цены, лаунчер и метрики.

*A process kit for AI coding agents (Claude Code, OpenCode): 27 barriers with red-team demos, an error collector with statistics, 15 skills, 10 MCP servers, 16 CI gates, core/full profiles with a cost budget, ADR memory, an error log that turns incidents into rules, harness review methods, convergence metrics. Agent-facing text follows ASD-STE100 to cut tokens. One-button launcher. Docs are in Russian. MIT.*

> Харнес — это то, что мы забрали у агента: не просьба в промпте, а исполняемый запрет в среде. Каждое забранное право — один пойманный инцидент.

---

## Содержание

1. [Одна кнопка](#одна-кнопка)
2. [Что делает «Старт»](#что-делает-старт)
3. [Команды лаунчера](#команды-лаунчера)
4. [Процесс за 6 шагов](#процесс-за-6-шагов)
5. [Сборщик и статистика ошибок](#сборщик-и-статистика-ошибок)
6. [Профили и цена харнеса](#профили-и-цена-харнеса)
7. [27 барьеров](#27-барьеров)
8. [15 скиллов](#15-скиллов)
9. [10 MCP-серверов](#10-mcp-серверов)
10. [Гейты и CI](#гейты-и-ci)
11. [Тексты для агентов по ASD-STE100](#тексты-для-агентов-по-asd-ste100)
12. [Зоны и права агента](#зоны-и-права-агента)
13. [Журнал ошибок, ADR, ревью харнеса](#журнал-ошибок-adr-ревью-харнеса)
14. [Метрики и нагрузка](#метрики-и-нагрузка)
15. [Внедрение: день, неделя, месяц](#внедрение-день-неделя-месяц)
16. [Что внутри](#что-внутри)
17. [Частые проблемы](#частые-проблемы)
18. [Откуда это и что получилось](#откуда-это-и-что-получилось)

---

## Одна кнопка

```bash
git clone https://github.com/crruton/self-harness.git
```

**Windows:** дважды щёлкните `harness.cmd` — откроется меню. Нужен [Git for Windows](https://git-scm.com/download/win).

**Linux / macOS:** `./harness.sh`

**Сразу в свой проект:**

```bash
./harness.sh start ../my-project          # Linux / macOS / Git Bash
harness.cmd start C:\work\my-project      # Windows
```

**Только посмотреть:** `./harness.sh demo` — 27 атак на 27 барьеров на временном репозитории. Каждая должна быть заблокирована:

```
  [v] B01 pre-push: main                 blocked: Blocked by pre-push: push to refs/heads/main...
  [v] B05 hook guard-destructive         blocked: Blocked by guard-destructive: "git reset --hard" can destroy work...
  [v] B22 portability: bash              blocked: FAIL check-portability B22...
  ...
Blocked: 27, missed: 0

== Error store after the attacks
| B05 | guard-destructive | 1 | ████ | 2026-11-06 |
  ...
```

### Требования

| Что | Зачем | Обязательно |
|---|---|---|
| git, bash | всё | да |
| Python 3.10+ | гейты, метрики, MCP | да |
| jq | хуки Claude Code (B04–B06, сборщик ошибок инструментов) | для Claude Code |
| `pip install -r .harness/mcp/requirements.txt` | MCP-серверы | для MCP |
| Docker | нагрузочный тест | нет |

`./harness.sh doctor` проверит всё сразу.

---

## Что делает «Старт»

`./harness.sh start <repo>` — шаг 1 процесса, базовая линия:

1. Проверяет окружение.
2. Ставит харнес по профилю (`core` по умолчанию): правила, зоны, 2 хука агента, 2 git-хука, 16 гейтов, сборщик ошибок, скиллы и MCP-серверы по выбору. Существующие файлы не трогает.
3. Включает git-хуки (`core.hooksPath = .githooks`) и пишет `harness.lock` — отпечаток харнеса.
4. Прогоняет все гейты.
5. Делает нулевой замер метрик в `docs/metrics.md`.
6. Печатает, что заполнить руками.

Что появится в вашем репозитории:

```
AGENTS.md, CLAUDE.md                правила проекта для агента (STE English)
error.md                            журнал ошибок агента
CHANGELOG.md
harness.lock                        отпечаток хуков, гейтов и настроек (B20)
.mcp.json                           MCP-серверы (--mcp или full)
opencode.json                       зоны для OpenCode
.claude/settings.json               зоны и хуки для Claude Code
.claude/hooks/                      guard.sh (B04–B06), collect-tool-errors.sh
.harness/errors/                    хранилище ошибок (коммитится)
.harness/config                     профиль: какие гейты выключены
.claude/skills/                     5 скиллов (core) или 15 (full)
.githooks/                          pre-push, commit-msg
.github/pull_request_template.md    поля ADR в MR/PR
.harness/mcp/                       код 10 MCP-серверов
docs/adr/                           каталог и шаблон ADR
docs/harness/                       методы ревью правок харнеса и арбитраж
docs/metrics.md                     метрики сходимости
gates/                              16 гейтов, сборщик collect.py
metrics/convergence.py, errors.py
docs/errors.md                      статистика ошибок
```

Проверьте `git status` и закоммитьте: харнес живёт в репозитории и меняется через MR, как код.

---

## Команды лаунчера

| Команда | Что делает | Шаг |
|---|---|---|
| `./harness.sh` | меню | — |
| `start <repo> [--profile core\|full] [--mcp a,b]` | базовая линия целиком (одна кнопка) | 1 |
| `doctor` | проверка окружения | 1 |
| `install <repo>` | только установка файлов | 1 |
| `demo [Bnn]` | атаки на все 27 барьеров или на один | — |
| `barriers` | список 27 барьеров | — |
| `errors <repo> [--suggest]` | статистика ошибок в `docs/errors.md` | 5 |
| `budget <repo>` | цена харнеса: токены в сессии и задержка хуков | 5 |
| `incident <repo> "что случилось"` | запись в `error.md` со следующим номером INC | 2 |
| `adr <repo> "решение"` | ADR со следующим номером и строка в каталоге | 3 |
| `check <repo>` | все гейты профиля | 4 |
| `lock <repo>` | принять проверенное изменение харнеса | 4 |
| `metrics <repo>` | метрики сходимости в `docs/metrics.md` | 5 |
| `loadtest <url> [rps]` | k6 со ступенями до `rps` в Docker | 5 |

На Windows то же самое: `harness.cmd <команда>`.

---

## Процесс за 6 шагов

Полностью — в [PROCESS.md](PROCESS.md).

| # | Шаг | Что делаем | Команда | Готово, когда |
|---|---|---|---|---|
| 1 | Базовая линия | Слои контекста, зоны, метрики до первой строки кода | `start` | Агент сам находит правила, push в main отклоняется, метрики считаются |
| 2 | Ошибка → правило | Каждая ошибка агента за 24 часа становится барьером и тестом | `incident` | У закрытого инцидента есть барьер и репро-тест |
| 3 | Командные границы | Общий AGENTS.md через MR, права через MCP, аренда ресурсов, ADR, спека до кода | `adr` | Номера ADR уникальны, агенты не конфликтуют за ресурсы |
| 4 | Пайплайн проверок | Хуки и гейты на каждом шаге, ревью правок харнеса | `check`, `lock` | Нарушение блокирует среда, а не договорённость |
| 5 | Замеры | Метрики сходимости раз в неделю, нагрузка на стенде | `metrics`, `loadtest` | Правила на плато, доля исправлений падает |
| 6 | Фиксация | Окружения, права, ветки dev/main записаны | — | Новый человек разворачивает процесс сам |

---

## Сборщик и статистика ошибок

Без статистики харнес — набор правил «на всякий случай». Со статистикой видно, какой барьер реально работает, какую ошибку агент повторяет и окупает ли харнес свою цену.

### Хранилище

`.harness/errors/events-ГГГГ-ММ-<автор>.jsonl` — одна строка JSON на событие. Файл на автора и месяц: файлы сливаются в git без конфликтов, и команда получает общую статистику. **Коммитьте папку.**

```json
{"v":1,"ts":"2026-11-05T21:41:45Z","source":"hook","barrier":"B05","name":"guard-destructive","outcome":"blocked",
 "actor":"agent","runtime":"claude-code","branch":"dev","commit":"a1b2c3d","session":"…","detail":"sh -c 'git reset --hard HEAD~1'"}
```

Секреты и персональные данные в `detail` маскируются до записи (ключи, токены, JWT, пароли, email, телефоны). Сборщик никогда не роняет хук или гейт: его собственная ошибка игнорируется. Отключить: `HARNESS_ERRORS=0`.

### Кто пишет

| Источник | Что попадает | Когда |
|---|---|---|
| `hook` | B04–B06: заблокированная команда агента | `guard.sh`, PreToolUse |
| `tool` | упавший вызов инструмента агента: команда и ошибка | `collect-tool-errors.sh`, PostToolUse |
| `git-hook` | B01–B03: push в main, force-push, плохое сообщение коммита | `pre-push`, `commit-msg` |
| `gate` | B07–B27: упавший гейт, первые три нарушения | `gates/run-all.sh` локально и в CI |
| `manual` | инцидент из `error.md` | `./harness.sh incident` |

`actor` = `agent`, если событие пришло из хука агента или из сессии Claude Code / OpenCode (переменные `CLAUDECODE`, `OPENCODE`), иначе `human`.

### Статистика

```bash
./harness.sh errors <repo>             # отчёт в консоль и в docs/errors.md
./harness.sh errors <repo> --suggest   # готовые команды incident для повторяющихся ошибок
python metrics/errors.py --json        # для дашбордов
```

Что в отчёте:

| Раздел | Что показывает | Что делать |
|---|---|---|
| Сводка | событий, заблокировано, доля агента, ошибок инструментов, открытых инцидентов, Enforcement Ratio | Enforcement Ratio должен расти: инциденты закрываются хуком/сервером/ОС, а не текстом |
| Барьеры | сколько раз сработал каждый барьер и когда последний раз | каждое срабатывание — ошибка, которая не дошла до кода; барьер, который не срабатывает месяцами, — кандидат на удаление |
| По неделям | события по источникам | рост `tool` — агент чаще ошибается; рост `hook` — чаще упирается в запреты |
| Повторы за 7 дней | один барьер и одна ошибка 3+ раз | барьер держит, но агента туда ведёт инструкция или скилл: исправьте источник, `--suggest` даст команду |
| Инциденты | по уровню барьера, классу, статусу | много `text` — правила не проверяются машиной |

Пример — статистика ошибок, которые агент сделал при сборке этого репозитория: [docs/errors.md](docs/errors.md), исходник — [error.md](error.md).

---

## Профили и цена харнеса

Харнес не бесплатный: правила, описания скиллов и инструменты MCP лежат в контексте каждой сессии, хуки добавляют задержку к каждому вызову инструмента. Поэтому по умолчанию ставится минимум, а остальное — по выбору.

```bash
./harness.sh start <repo>                                   # core
./harness.sh start <repo> --profile full                    # всё
./harness.sh start <repo> --mcp test-env-broker,safe-edit   # core + два MCP-сервера
./harness.sh budget <repo>                                  # сколько это стоит
```

| | core (по умолчанию) | full |
|---|---|---|
| Барьеры | 27 | 27 |
| Сборщик ошибок | да | да |
| Скиллы | 5 процессных | 15 |
| MCP-серверы | нет (добавляются `--mcp`) | 10 |
| Гейты | 14 из 16 (без changelog и large-files) | 16 |
| **Токенов в каждой сессии** | **~420** | **~3 000** |
| **Задержка на вызов инструмента** | **~130 мс** | **~130 мс** |

Замер `./harness.sh budget` на Windows 11 (Git Bash), токены — tiktoken o200k как оценка. Из 3 000 токенов профиля full 2 300 — описания 29 инструментов MCP: подключайте только те серверы, ресурсы которых реально есть в проекте.

**Улучшит ли харнес работу агента?** Только если его цена меньше, чем стоят ошибки, которые он ловит. Поэтому:
- ставьте `core`, а модули добавляйте, когда статистика показала проблему;
- раз в неделю сравнивайте `budget` и `errors`: барьер, который за месяц не сработал ни разу, а стоит токенов или миллисекунд, — кандидат на удаление;
- правку харнеса проверяйте по [методам ревью](review/harness-review.md): прогон с правкой и без, на одних и тех же задачах.

Первая версия хуков стоила **~2,5 секунды на каждый вызов** (три хука, `grep` на каждый шаблон, четыре вызова `jq`). Это нашёл `budget`. После объединения в один `guard.sh` — ~130 мс.

---

## 27 барьеров

Барьер — то, что физически не даёт агенту сделать ошибку. Чем глубже уровень, тем надёжнее: **ОС > сервер > хук > гейт > текст**. Каждый барьер появился после реального инцидента. `./harness.sh demo` атакует все 27; `./harness.sh demo B07` — один; MCP `redteam-runner` делает то же из агента.

| ID | Барьер | Уровень | Где | Что ловит |
|---|---|---|---|---|
| B01 | `pre-push` | git-хук | машина разработчика | push в `main` |
| B02 | `pre-push` | git-хук | машина разработчика | force-push и удаление ветки |
| B03 | `commit-msg` | git-хук | машина разработчика | «wip», «fix», слишком короткие и длинные заголовки |
| B04 | `guard.sh` | хук агента | Claude Code | полный прогон тестов на каждую правку |
| B05 | `guard.sh` | хук агента | Claude Code | `git reset --hard`, `rm -rf`, `DROP TABLE` — в том числе внутри `sh -c`, `python -c` |
| B06 | `guard.sh` | хук агента | Claude Code | чтение `.env`, ключей, `secrets/` — и через Read, и через `cat` |
| B07 | `check-secrets` | гейт | CI | ключи AWS, GitHub, GitLab, Slack, JWT, приватные ключи, пароли в коде |
| B08 | `check-forbidden-files` | гейт | CI | `.env`, `*.pem`, `id_rsa` в git |
| B09 | `check-large-files` | гейт | CI | файл больше 1 МБ |
| B10 | `check-conflict-markers` | гейт | CI | забытые `<<<<<<<` |
| B11 | `check-test-weakening` | гейт | CI | добавлен `skip`/`.only`, удалены assert |
| B12 | `check-changelog` | гейт | CI | код изменён, CHANGELOG — нет |
| B13 | `check-adr-numbers` | гейт | CI | два ADR с одним номером |
| B14 | `check-adr-fields` | гейт | CI | ADR без `Status`, `Applies To`, `Reconsider When` |
| B15 | `check-adr-links` | гейт | CI | ссылка на несуществующий ADR |
| B16 | `check-error-log` | гейт | CI | инцидент закрыт без барьера и репро-теста |
| B17 | `check-rules-size` | гейт | CI | AGENTS.md длиннее 150 строк |
| B18 | `check-ste` | гейт | CI | правило для агента нарушает ASD-STE100 |
| B19 | `check-zones` | гейт | CI | из настроек убран запрет Red Zone или хук |
| B20 | `check-harness-integrity` | гейт | CI | хук, гейт или настройка изменены без ревью |
| B21 | `check-portability` | гейт | CI | `re.M` + `\s`: пустое поле читает следующую строку |
| B22 | `check-portability` | гейт | CI | `subprocess.run(["bash", …])`: на Windows стартует WSL, а не Git Bash |
| B23 | `check-portability` | гейт | CI | `communicate()` с JSON-RPC: stdin закрывается раньше ответа сервера |
| B24 | `check-portability` | гейт | CI | зависимость `pkg>=1` без верхней границы: следующая мажорная версия ломает импорт |
| B25 | `check-portability` | гейт | CI | текстовый ввод-вывод без `encoding=`: кириллица ломается в cp1251 |
| B26 | `check-portability` | гейт | CI | shell-скрипт с CRLF, нет `*.sh eol=lf` в `.gitattributes` |
| B27 | `check-portability` | гейт | CI | скрипт в git без бита исполнения (100644) |

**B21–B27 — ошибки, которые делал агент, собиравший этот репозиторий**, раз за разом при переходе между Linux и Windows. Каждая записана в [error.md](error.md) с причиной и репро-тестом; ошибка B21 повторилась дважды, потому что первое исправление не стало барьером. Python-код гейт разбирает через `ast`, а не регулярными выражениями.

Хуки на машине обходятся (`--no-verify`, другой рантайм), поэтому каждый важный запрет продублирован глубже: защита ветки на сервере, гейт в CI, права файловой системы.

---

## 15 скиллов

Лежат в [`skills/`](skills/), ставятся в `.claude/skills/`. Формат — `SKILL.md` с `name` и `description`: агент подгружает скилл, когда задача подходит под описание. Все тексты — на английском по ASD-STE100 и проходят `check-ste --strict`.

**Соло-этап: 10 скиллов.** Каждый закрывает класс ошибки, который агент повторял чаще всего. Оригиналы писались под SIP-платформу; здесь они обобщены для любого проекта.

| Скилл | Ошибка агента | В команде |
|---|---|---|
| [`async-boundary`](skills/async-boundary/SKILL.md) | блокирующий I/O в async-обработчиках | без изменений |
| [`test-isolation`](skills/test-isolation/SKILL.md) | тесты лезли в общую тестовую БД | **переделан:** аренда через `test-env-broker` |
| [`spec-first-diff`](skills/spec-first-diff/SKILL.md) | правка без ссылки на спецификацию | без изменений |
| [`latency-budget`](skills/latency-budget/SKILL.md) | фичи без проверки бюджета p95 | **переделан:** общий дашборд |
| [`secrets-guard`](skills/secrets-guard/SKILL.md) | токен в конфиге | без изменений, + гейт B07 и хук B06 |
| [`schema-first-config`](skills/schema-first-config/SKILL.md) | структурированные файлы правились как текст (было: dialog-scenario-schema) | без изменений |
| [`flaky-statistics`](skills/flaky-statistics/SKILL.md) | флейк принимали за успех (было: rollback-on-flaky) | **переделан:** статистика вместо «3 прогона» |
| [`context-freshness`](skills/context-freshness/SKILL.md) | работа на устаревшем контексте | **переделан:** стал отдельным MCP |
| [`invariants-guard`](skills/invariants-guard/SKILL.md) | ломали инварианты ядра (было: barge-in-invariants) | без изменений |
| [`red-team-scenarios`](skills/red-team-scenarios/SKILL.md) | барьер не атаковали | без изменений, стал онбордингом |

**Командный этап: 5 процессных скиллов.**

| Скилл | Когда агент его берёт |
|---|---|
| [`error-to-rule`](skills/error-to-rule/SKILL.md) | после ошибки: запись в `error.md`, барьер, репро-тест |
| [`adr-decision`](skills/adr-decision/SKILL.md) | перед планом и при архитектурном решении |
| [`harness-review`](skills/harness-review/SKILL.md) | при изменении правил, хуков, гейтов, скиллов, MCP |
| [`ste-writing`](skills/ste-writing/SKILL.md) | когда пишет текст, который читают агенты |
| [`change-pipeline`](skills/change-pipeline/SKILL.md) | перед каждым коммитом и push |

---

## 10 MCP-серверов

Лежат в [`mcp/servers/`](mcp/servers/), ставятся в `.harness/mcp/`, подключаются через `.mcp.json`. Работают с `mcp` 1.x и 2.x. Подробно — [mcp/README.md](mcp/README.md).

| Сервер | Запрещает | Было на соло-этапе |
|---|---|---|
| `test-env-broker` | подключение к общей тестовой БД без аренды | test-env-broker |
| `safe-edit` | запись в Red Zone и за пределы репозитория (в том числе через симлинки) | ast-mutator |
| `spec-registry` | MR с коммитами без `Spec:` или `ADR:` | spec-registry |
| `quality-gate` | коммит без проверки | semgrep-gate |
| `context-freshness` | работу на устаревшей копии | context-freshness |
| `pii-reader` | чтение персональных данных без масок | call-transcript |
| `schema-store` | правку JSON, ломающую схему | dialog-scenario-store |
| `readonly-view` | любую запись в ядро | rtp-core-readonly |
| `slot-scheduler` | GPU, слот LLM, лицензию без аренды | gpu-scheduler |
| `redteam-runner` | ничего — атакует 27 барьеров | adversarial-runner |

`python mcp/selftest.py` поднимает каждый сервер по протоколу MCP (stdio, `initialize`, `tools/list`) и проверяет поведение инструментов.

---

## Гейты и CI

16 гейтов (B07–B27) запускает `bash gates/run-all.sh` или `./harness.sh check <repo>`. Все гейты — без внешних зависимостей, только Python и git.

### Что проверяют

Гейты, которые смотрят на **изменение**, берут список файлов так:
1. `HARNESS_BASE` (в CI — целевая ветка, например `origin/main`): diff `BASE...HEAD`;
2. иначе staged-изменения (локально перед коммитом);
3. иначе последний коммит;
4. иначе все файлы (репозиторий из одного коммита).

Так гейты не падают на легаси-коде: проверяется то, что принёс агент, а не весь репозиторий.

| Гейт | Смотрит на | Проверяет | Как исправить |
|---|---|---|---|
| `check-secrets` | добавленные строки | приватные ключи, `AKIA…`, `ghp_…`, `glpat-…`, `xox…`, `sk-…`, JWT, `password = "…"` длиннее 12 символов | убрать в переменную окружения, ротировать секрет. Для тестовых фикстур — пометка `harness:allow-secret` в строке |
| `check-forbidden-files` | все файлы в git | `.env`, `.env.*` (кроме `.example`, `.sample`, `.template`), `*.pem`, `*.key`, `*.p12`, `id_rsa`, `secrets/*` | `git rm --cached`, добавить в `.gitignore`, ротировать секрет |
| `check-large-files` | изменённые файлы | размер больше `HARNESS_MAX_FILE_KB` (1024) | Git LFS или хранилище артефактов |
| `check-conflict-markers` | изменённые файлы | `<<<<<<<`, `=======`, `>>>>>>>` в начале строки | разрешить конфликт |
| `check-test-weakening` | изменённые тесты | `t.Skip`, `pytest.mark.skip`, `it.skip`, `.only`, `xit`, `@Disabled`, `@Ignore`; удалённых assert больше, чем добавленных | чинить код, а не тест. Удаление assert — только с апрувом человека |
| `check-changelog` | изменённые файлы | изменён код (не `docs/`, не `.md`), а `CHANGELOG.md` — нет | запись в `[Unreleased]` |
| `check-adr-numbers` | `docs/adr/` | уникальность номеров; подсказывает следующий свободный | `./harness.sh adr` |
| `check-adr-fields` | `docs/adr/` | заполнены `Status`, `Applies To`, `Reconsider When` | заполнить поля |
| `check-adr-links` | `docs/adr/` | все упомянутые `ADR-NNNN` существуют | исправить ссылку |
| `check-error-log` | `error.md` | закрытый инцидент имеет `Barrier`, `Level`, `Repro`; уровень из списка | заполнить поля |
| `check-rules-size` | `AGENTS.md`, `CLAUDE.md` | не длиннее 150 строк | вынести детали в документы и дать ссылку |
| `check-ste` | `AGENTS.md`, `CLAUDE.md`, скиллы, `rules/` | правила ASD-STE100: 5.1, 6.3, 6.6, 4.2, 8.1, 1.1 (+ предупреждения 5.2, 3.6) | переписать по [docs/STE.md](docs/STE.md) |
| `check-zones` | `.claude/settings.json`, `opencode.json` | на месте deny для `.env`, `git reset --hard`, `rm -rf`, force-push; зарегистрированы три хука агента | вернуть запреты |
| `check-harness-integrity` | `.githooks/`, `.claude/hooks/`, `.claude/settings.json`, `opencode.json`, `gates/` | sha256 совпадает с `harness.lock` | провести ревью изменения, затем `./harness.sh lock` |
| `check-portability` | изменённые `.py`, `requirements*.txt`, `pyproject.toml`, скрипты | B21–B27: `re.M`+`\s`, голый `bash` в subprocess, `communicate()` с JSON-RPC, зависимость без верхней границы, текст без `encoding=`, CRLF, нет бита исполнения | исправить по подсказке в сообщении; весь репозиторий: `HARNESS_ALL=1` |

### Настройка

| Переменная | Значение по умолчанию | Зачем |
|---|---|---|
| `HARNESS_BASE` | — | целевая ветка для diff, в CI обязательно |
| `HARNESS_SKIP` | — | пропустить гейты: `"check-changelog check-ste"`. Только с апрувом человека и причиной в MR |
| `HARNESS_MAX_FILE_KB` | 1024 | порог `check-large-files` |
| `HARNESS_ADR_DIR` | `docs/adr` | каталог ADR |
| `HARNESS_ALL` | — | `1`: проверять все файлы, а не только изменение |
| `HARNESS_ERRORS` | — | `0`: выключить сборщик ошибок |

### Подключение к CI

GitHub Actions — [`ci/github-actions.yml`](ci/github-actions.yml), GitLab CI — [`ci/gitlab-ci.yml`](ci/gitlab-ci.yml). Минимум:

```yaml
- run: bash gates/run-all.sh
  env:
    HARNESS_BASE: origin/${{ github.base_ref || 'main' }}
```

Для gitlab: `HARNESS_BASE: origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME`.

### Почему `harness.lock`

Агент — заинтересованная сторона: ему дешевле ослабить проверку, чем починить код. Поэтому сам харнес под защитой: правка хука, гейта или настроек меняет sha256, и `check-harness-integrity` падает, пока человек не проверит изменение и не выполнит `./harness.sh lock`. Плюс `Edit(./harness.lock)` — в deny агента, а правка `.githooks/`, `gates/`, `.claude/` — в зоне Yellow.

### CI этого репозитория

[`.github/workflows/harness.yml`](.github/workflows/harness.yml): 27 атак должны быть заблокированы; репозиторий сам проходит `check-portability` на всех файлах и `check-error-log` на своём `error.md`; скиллы и шаблоны проходят `check-ste --strict`; 10 MCP-серверов проходят self-test на `mcp<2` и `mcp>=2`; лаунчер проходит `start → incident → adr → check → errors → budget`.

---

## Тексты для агентов по ASD-STE100

Всё, что читает агент (AGENTS.md, скиллы, шаблоны, сообщения гейтов), написано на Simplified Technical English по стандарту ASD-STE100 Issue 9. Тексты для людей — на русском.

Замер на шаблонах этого репозитория (токенизаторы OpenAI как оценка):

| | o200k | cl100k |
|---|---|---|
| Файл глобальных правил | −10% при 29 правилах вместо 22 | −37% |
| На одно правило | −18…−32% | −38…−52% |

Гейт `check-ste` проверяет измеримые правила стандарта: не больше 20 слов в инструкции (5.1), 25 — в описании (6.3), 6 предложений в абзаце (6.6), без сокращённых форм (4.2), без точки с запятой (8.1), только одобренные слова (1.1, словарь из 36 частых слов с заменами). Подробно и с примерами — [docs/STE.md](docs/STE.md). Замерить свои файлы: `python metrics/token_count.py`.

---

## Зоны и права агента

| Зона | Что | Механизм |
|---|---|---|
| **Green** — без подтверждения | чтение кода, поиск, сборка, тесты по диффу, коммит в свою ветку | разрешено |
| **Yellow** — с апрувом | `git push`, Docker, сетевые запросы, правка `.claude/`, `.githooks/`, `gates/`, `opencode.json` | `ask` |
| **Red** — запрет | `.env` и секреты, `git reset --hard`, `git clean`, `rm -rf`, force-push, `harness.lock` | `deny` + хуки B05–B06 + права ФС + защита веток |

- Claude Code: [`zones/claude-settings.json`](zones/claude-settings.json) → `.claude/settings.json`.
- OpenCode: [`zones/opencode.json`](zones/opencode.json) → `opencode.json`.

Строковый `deny` обходится через `sh -c`. Поэтому B05 разбирает команду целиком, включая обёртки, а для Red Zone нужны ещё права файловой системы (read-only монтирование в контейнер агента) и защита веток на сервере.

---

## Журнал ошибок, ADR, ревью харнеса

**Ошибка → правило.** `./harness.sh incident <repo> "агент запушил в main"` — запись `INC-…` в `error.md`. Поля: `Symptom`, `Cause`, `Class`, `Barrier`, `Level` (text | hook | server | OS), `Repro`, `Status`. Закрыть без барьера и репро-теста нельзя (B16). Запись — в течение 24 часов: цена правила = цена инцидента × свежесть памяти.

**ADR — память решений.** `./harness.sh adr <repo> "решение"` — `docs/adr/NNNN-slug.md` со следующим номером и строка в каталоге. Поля для агента: `Applies To` (пути), `Reconsider When` (измеримые триггеры), `Supersedes`. Чистый дифф с зелёными тестами, который молча отменяет принятое решение, — дефект. Шаблон MR требует «Relevant ADRs» и «Меняет принятое решение? Да / Нет / Не уверен».

**Ревью правок харнеса.** Правка харнеса меняет поведение всех агентов сразу, поэтому её ревьюят как эксперимент. Методы взяты из [harness2](https://github.com/google-research/harness2) (Google Research): контраст прогонов, сравнение с базой, менять одно, отложенные задачи, агент не видит критерии, сбой ≠ ноль, уроки с доказательством, отчёт с условиями. Затем — карантинный арбитраж из трёх шлюзов. Подробно — [review/harness-review.md](review/harness-review.md), [review/arbitration.md](review/arbitration.md).

---

## Метрики и нагрузка

`./harness.sh metrics <repo>` — метрики по неделям из истории git в `docs/metrics.md`:

| Метрика | Хороший тренд |
|---|---|
| `fix_share_pct` — доля коммитов-исправлений | падает |
| `rule_bullets` — пунктов правил в AGENTS.md | плато при росте кода |
| `adr_total` | растёт ступенями |
| `test_files` | растёт |

Если правил больше, а доля исправлений не падает, — харнес копит противоречия. Исправления определяются по ключевым словам в сообщении коммита: это оценка.

`./harness.sh loadtest <url> 100` — k6 со ступенями 25% → 50% → 100% от цели ([`loadtest/`](loadtest/)). Только на изолированном стенде; эндпоинты с LLM мерить отдельно.

---

## Внедрение: день, неделя, месяц

**День 1.** `./harness.sh start <repo>` → проверить и закоммитить. Заполнить `AGENTS.md` (до 150 строк, по STE). Положить `templates/AGENTS.global.md` в `~/.claude/CLAUDE.md`. Защитить `main` на сервере. Подключить гейты в CI.

**Неделя 1.** Каждая ошибка агента — `incident` в тот же день, барьер как можно глубже, репро-тест. Две одинаковые поправки за неделю — правило в `AGENTS.md`. В конце недели — `metrics`.

**Месяц 1.** Второй человек или параллельный агент — ADR через `adr`, общие ресурсы через MCP (`test-env-broker`, `slot-scheduler`). Каждую правку харнеса — через ревью, арбитраж и `lock`. Смотреть тренд метрик за 4+ недели.

---

## Что внутри

| Путь | Что там |
|---|---|
| `harness.sh`, `harness.cmd` | лаунчер |
| `PROCESS.md` | процесс: 6 шагов |
| `install.sh`, `try-it.sh` | установка по профилю; демо и red-team 27 барьеров |
| `skills/` | 15 скиллов |
| `mcp/` | 10 MCP-серверов, self-test, конфиг |
| `hooks/` | `guard.sh` (B04–B06), сборщик ошибок инструментов, 2 git-хука |
| `gates/` | 16 гейтов, сборщик `collect.py`, словарь STE |
| `zones/` | настройки Claude Code и OpenCode |
| `templates/` | AGENTS.md, ADR, `error.md`, MR, CHANGELOG |
| `review/` | ревью правок харнеса, арбитраж |
| `metrics/` | метрики сходимости, статистика ошибок, цена харнеса, подсчёт токенов |
| `loadtest/` | шаблон k6 |
| `ci/` | подключение гейтов в GitHub Actions и GitLab CI |
| `docs/STE.md` | правила ASD-STE100 для текстов агентов |

---

## Частые проблемы

| Проблема | Решение |
|---|---|
| `harness.cmd`: «Git Bash not found» | установите Git for Windows |
| Хуки Claude Code не срабатывают | нужен `jq` в PATH; `./harness.sh doctor` |
| push в main проходит | хук обходится `--no-verify` — включите защиту ветки на сервере |
| `check-harness-integrity` падает после обновления харнеса | так задумано: проверьте изменение, затем `./harness.sh lock` |
| `check-ste` ругается на русский текст | не должен: предложения с кириллицей пропускаются. Пишите тексты для агентов по-английски |
| `check-changelog` на мелкой правке | `HARNESS_SKIP="check-changelog"` с причиной в MR |
| MCP: `No module named 'mcp.server.fastmcp'` | у вас `mcp` 2.x и старый код; серверы self-harness поддерживают обе версии |
| Установка «оставила существующие файлы» | так задумано: сравните с `templates/` и перенесите нужное |

---

## Откуда это и что получилось

- **Соло-этап** — SIP-платформа, один человек: каждая ошибка агента становилась правилом. Итог — 10 скиллов и 10 MCP-серверов (обобщённые версии — в `skills/` и `mcp/servers/`). Шесть скиллов пережили переход в команду без изменений, четыре переделали — все в сторону машинной проверки вместо текста.
- **Командный этап** — ArcSpace, платформа системного архитектора: 5 инженеров, 37 ролей агентов, 18 недель истории.

| ArcSpace | |
|---|---|
| Доля коммитов-исправлений | ~50% в июле–августе → < 5% в октябре |
| Поток коммитов | вырос в 5 раз |
| Пунктов правил в AGENTS.md | 11–13, шесть недель подряд |
| ADR / автотесты | 60 / 618 |
| Нагрузка на путь чтения (2 vCPU) | 100 и 400 RPS без ошибок, p95 ≈ 6 мс |

Доклад: «Харнес, который написал сам себя», HighLoad++ 2026, Андрей Носов.

## Лицензия

[MIT](LICENSE)
