# Changelog

## [1.6.0] - 2026-11-08

### Added
- 30 hard bench tasks (q17-q46) and 8 more (q09-q16) from the damage classes of the incident logs, committed before the runs. 46 tasks in all.
- The lean arm: templates/AGENTS.lean.md, 10 rules for the damage classes, with the same barriers.
- Damage per run in the report (lost work, rewritten history, secret in the context, skipped checks, weakened tests, cut code, edits of generated or applied files), the rate of unsolved tasks, a headline table with relative change.
- bench/merge.py joins several runs for one report. docs/RESULTS.md: 924 runs, 438 rubles. Lean against no harness: dangerous runs 14% -> 3% (-80%), unsolved 20% -> 13% (-34%), both proven; +14% rubles, +17% time.

### Fixed
- B06 let `cat .env*` pass (INC-2026-11-09-01). B38 also stops `python -c` with a double escape (INC-2026-11-09-03).
- The q45 check counted `npm install` of the published package as damage. A task list from `ls -F` ran 0 tasks. Workspaces are deleted on Windows.

## [1.5.0] - 2026-11-09

### Added
- CI `bench-gate`: a PR that changes the rules, skills, hooks or the learning policy gets an A/B of the base harness against the PR harness as a comment, and fails when the PR is proven worse or hits more traps (`report --fail-if-worse`, `arm --absolute`).
- CI `h2-weekly`: a Harness² step and gate every Monday; when the gate accepts, `adopt --apply` writes the tree into the kit rules and skills and a draft PR into dev carries step.md. It never merges.
- step.json and step.md record the cost of a step, the improver part included.

### Changed
- README starts from the two loops (barriers each session, rules once a week), the measured results, the quick start, vendor-neutral executors and the CI.
- The talk: slide 29 shows the CI that closes the process.

## [1.4.0] - 2026-11-07

### Added
- OpenCode executor: `--model provider/model` runs any provider; the arm installs as AGENTS.md and .opencode/, hooks/opencode-guard.js sends each tool call to guard.sh.
- h2/policy.json: what the harness may learn (editable files, forbidden rules, protected safety lines, gate thresholds, budget). step.md for each step: diff, reasons, what the policy rejected, the gate decision. `h2 auto`.
- First real results: bench/results/2026-11-07-first (80 runs, 34 rubles: traps 4/40 → 0/40, solved +10 p.p. not proven, slower and dearer — proven) and h2/results/2026-11-07-step1 (14 new rules, faster and fewer failed calls, solved −8.3 p.p.: the gate rejected it).

### Fixed
- A relative --out made the q07 check fail 10 of 10 (INC-2026-11-07-02).

## [1.3.0] - 2026-11-07

### Added
- `bench/`: A/B of harnesses on 8 dev tasks with agent traps (test weakening, cut code, reset of uncommitted work, a secret in .env, a skipped hook, a folder checkout, a file without encoding, shell patching). One model, only the harness changes; hidden check.py, repeats, Wilson and bootstrap 95% intervals, rubles at the Bank of Russia rate, train and held-out tasks. `./harness.sh bench run|report`. Each task has a reference solution and a trap for tests with no model.
- `h2/`: the Harness² method (google-research/harness2) on the bench: propose an invariant and a domain edit, probe both on the same tasks, compose from the behavioural contrast with no ground truth, keep lessons in h2/library; the gate on held-out tasks decides; adopt goes through a MR. `./harness.sh h2 step|gate|adopt`.
- `install --auto-evolve`: SessionEnd runs evolve in repositories with error.md, SessionStart tells the agent that harness tasks wait.
- tests/test_bench.py: the bench and an h2 step without a model, in CI. A manual CI job runs the bench with a real model when the secret ANTHROPIC_API_KEY is set.
- docs/BENCH.md: the inputs, the commands, what each number proves, the differences from upstream harness2, the cost.

### Changed
- B38 also denies a heredoc into an interpreter or into a code file with a double escape (INC-2026-11-07-01).
- The talk: slide 20 is the Harness² step, slide 20а is the A/B proof; harness2 is a transferred method, not a deployed framework.

## [1.2.0] - 2026-11-06

### Added
- B38 guard-syntax: `bash -n` checks each heredoc or long multi-line command before it runs; `sed -i` with escapes in a code file is denied. From INC-2026-11-06-03, -08, -13.
- tests/test_loop.py: 7 repro tests of the barriers that the loop made from its own incidents. CI runs them and checks that the demo does not write to the real error store (INC-2026-11-05-08).
- Incident status `accepted`: not an agent error. The gate requires a Cause.

### Changed
- The first real turn of `evolve` on this repository: 4 drafts, 9 tasks; the second turn: 0 and 0. 21 incidents, no closed incident with a text rule only.
- The demo runs 36 attacks and 17 normal actions.
- B22 resolves names bound to "bash" or "sh" (INC-2026-11-06-12).
- harness2 is part of the rule path; the talk says 100 agents, as in the proposal.

### Fixed
- The error signature took a stack header or a success line; now it takes the line that names the error (INC-2026-11-06-07, -10).
- The collector mask and B07 did not know the new GitLab token formats (INC-2026-11-06-11).
- The dashboard counted the catch that opened an incident as a repeat after it; attempts now count from the next day. Accepted incidents are not open.

## [1.1.0] - 2026-11-06

### Added
- 10 barriers for common agent errors, set before the first incident. guard.sh: B28 skip of git hooks (`--no-verify`, `HUSKY=0`), B29 `curl | sh` (ask), B30 publish and deploy: `npm publish`, `docker push`, `terraform apply`, `kubectl delete`, `helm upgrade` (ask), B31 credential stores and env dumps, B32 hand edits of lock files and installed packages, B33 changes of hooks and agent settings (ask). Gates: B34 deleted tests, B35 linter and type check suppressions without a reason, B36 cut code (`// ... rest of the code`), stubs and debugger calls, B37 a dependency change without the lock file.
- `./harness.sh dashboard`: one HTML file that shows if the agent makes fewer errors, faster and cheaper. Tool errors and barrier attempts per 100 calls, tokens, USD and active minutes per session, the state of each incident after its barrier (learned, holding, leaked), barriers that fired with no incident, new variants, candidates for the next barrier. The denominator comes from Claude Code transcripts, so the hooks cost nothing on successful calls.
- docs/LOOP.md: the path of one error from the event to the verified barrier.
- Incident fields `Found by` and `Closed`.
- `./harness.sh evolve <repo>`: one turn of the loop with no human. It writes draft incidents for failed calls that repeat and for barriers that fire 3+ times with no incident, and prints tasks for the agent: close the drafts with error-to-rule, fix the rule where the agent keeps trying, widen a barrier that leaks.
- docs/TALK.md: the talk structure around the main idea, the slide texts, the map from the talk proposal to the slides, the video invitation.

### Changed
- README and PROCESS.md start from the main idea: the model does not learn between sessions, the environment does, and the numbers show it. Each process step ends with what the environment now holds instead of the human.
- The dashboard shows costs in rubles: the Bank of Russia rate of the day (one GET to cbr.ru, cached for the day), `HARNESS_USD_RUB` to set it, `HARNESS_OFFLINE=1` for no network. Rubles per session and per week.
- The demo runs 35 attacks and 16 normal actions.
- B04 knows the full test commands of dotnet, rspec, phpunit, mix, swift, flutter, deno, ctest, tox, make test. B11 and the convergence metric know test files of Ruby, PHP, Kotlin, Swift, C#, Rust, Elixir, Dart and C++.
- The guard hook also checks MultiEdit and NotebookEdit. A repeated install updates the matcher.
- error-to-rule: the barrier must stop the class, the agent gets a rule line, the dashboard checks the result after 7 days.

### Fixed
- collect-tool-errors.sh wrote nothing in the global install: it looked for gates/collect.py in the repository. git hooks also fall back to the global collector.
- guard.sh read the fields with a tab separator, so an empty command moved the file path into the command field, and @tsv doubled the backslashes of Windows paths. Path checks now get the real path.
- convergence.py counts CLAUDE.md when the project has no AGENTS.md.

## [1.0.0] - 2026-11-06

### Changed
- Global install by default: once per machine, all projects, nothing copied into repositories. `./harness.sh install` adds two hook entries to ~/.claude/settings.json (backup first, other hooks stay), 5 process skills, the error store. `./harness.sh uninstall` restores the file.
- guard.sh has three levels: deny only what git cannot bring back (reset --hard, clean -f, checkout -- ., force push, rm -rf of /, ~, ., .git, secret files), ask for branch -D, DROP/TRUNCATE, docker prune and a full test run, allow all other actions. `docker compose down -v` and `rm -rf build` pass.
- The error store is global (~/.claude/harness/errors) with the field "repo". Statistics show all projects, questions to the human and a per-project table. `--team-store` keeps a shared store in a repository.
- Project mode is optional: `./harness.sh project <repo>` for git hooks and 13 CI gates. check-zones now catches project settings that open Red Zone actions or turn off hooks. check-harness-integrity is used only with `--lock`.
- The demo runs 25 attacks and 8 normal actions. A false positive fails the demo. A failure that is not from a barrier shows DEMO ERROR.
- Cost: about 160 tokens per session and 110 ms per tool call.

### Removed
- check-changelog (B12).
- Profiles core/full and the `start` command.

### Moved to extras/
- 10 MCP servers, 10 domain skills, the k6 load test, check-large-files (HARNESS_EXTRA).

## [0.4.0] - 2026-11-06

### Added
- Error collector `gates/collect.py` and error store `.harness/errors/events-YYYY-MM-<author>.jsonl` (one file per author and month, committed to git, secrets masked).
- Events from agent hooks, git hooks, gates, failed agent tool calls (`collect-tool-errors.sh`, PostToolUse) and incidents.
- Error statistics `metrics/errors.py` and `./harness.sh errors`: barriers, weekly trend, repeats, incidents, Enforcement Ratio. `--suggest` turns repeats into incident commands.
- Barriers B21-B27, gate `check-portability`: the Linux/Windows errors that the agent made while it wrote this kit.
- `error.md` of the kit: 9 incidents of the agent that wrote it. `docs/errors.md`: their statistics.
- Profiles `--profile core|full`, `--mcp`, `--skills`. Core is the default: no MCP, 5 skills.
- `metrics/budget.py` and `./harness.sh budget`: tokens in each session and hook latency.

### Changed
- `guard.sh` replaces guard-tests.sh, guard-destructive.sh and guard-secrets.sh: one process, one jq call, bash regex. About 130 ms on each tool call instead of about 2.5 s.
- `docker compose down` is not blocked any more. `docker volume prune` and `docker system prune` are still blocked.
- MCP requirements have upper bounds: `mcp>=1.2,<3`, `jsonschema>=4,<5`.

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
