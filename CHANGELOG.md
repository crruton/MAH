# Changelog

## [0.3.0] - 2026-11-05

### Added
- 15 skills in `skills/`: 10 from the solo stage (generalized from the SIP platform) and 5 process skills. Installed to `.claude/skills/`.
- 10 MCP servers in `mcp/servers/`, with `mcp/selftest.py` (stdio protocol and behavior). Work with mcp 1.x and 2.x.
- 20 barriers with one attack each: `try-it.sh`, `./harness.sh demo [Bnn]`, MCP `redteam-runner`.
- New hooks: `guard-destructive.sh`, `guard-secrets.sh`, `commit-msg`. `pre-push` also blocks force push and branch deletion.
- New gates: check-secrets, check-forbidden-files, check-large-files, check-conflict-markers, check-test-weakening, check-changelog, check-adr-fields, check-adr-links, check-ste, check-zones, check-harness-integrity. Total: 14.
- `harness.lock` and `./harness.sh lock`: a harness change needs review.
- `docs/STE.md`, `gates/check-ste.py`, `gates/ste-wordlist.tsv`: agent text follows ASD-STE100 Issue 9.
- `metrics/token_count.py`.

### Changed
- Agent-facing templates are in Simplified Technical English.
- `error.md` fields are in English: Barrier, Level, Repro, Status.
- README: skills, MCP, 20 barriers, detailed gates and CI.

## [0.2.0] — 2026-11-05

### Added
- Лаунчер `harness.sh` и `harness.cmd` (Windows, двойной щелчок): меню и команды `start`, `doctor`, `demo`, `install`, `check`, `metrics`, `incident`, `adr`, `loadtest`.
- `start` — базовая линия одной командой: проверка окружения, установка, гейты, нулевой замер метрик, следующие шаги.
- Примеры подключения гейтов в GitHub Actions и GitLab CI (`ci/`).
- Лицензия MIT.

### Changed
- Подробный README: внедрение по дням, зоны, гейты, ADR, ревью, метрики, частые проблемы.
- Каталог ADR в шаблоне без строки-примера.

## [0.1.0] — 2026-11-05

### Added
- Процесс за 6 шагов (`PROCESS.md`) со входом, действиями, артефактом и критерием выхода каждого шага.
- Шаблоны: глобальный и проектный AGENTS.md, ADR с полями Applies To / Reconsider When / Supersedes, каталог ADR, `error.md`, шаблон MR, CHANGELOG.
- Зоны Green / Yellow / Red для Claude Code и OpenCode.
- Хуки: `pre-push` (запрет push в main), `guard-tests.sh` (запрет полного прогона тестов агентом).
- Гейты: уникальность номеров ADR, полнота записей `error.md`, размер AGENTS.md.
- Методы ревью правок харнеса, взятые из harness2, и карантинный арбитраж.
- Пример MCP-сервера аренды тестовых сред с TTL и очередью.
- `metrics/convergence.py` — метрики сходимости харнеса по истории git.
- Шаблон нагрузочного теста k6.
- `install.sh`, `try-it.sh` и CI, который проверяет, что пять барьеров блокируют.
