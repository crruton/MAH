# Changelog

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
