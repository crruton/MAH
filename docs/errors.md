# Статистика ошибок агентов

Обновлено: 2026-11-08. Команда: `./harness.sh errors .`

| Событий | Проектов | Заблокировано | Вопросов человеку | Доля агента | Ошибок инструментов | Инцидентов | Открытых | Enforcement Ratio |
|---|---|---|---|---|---|---|---|---|
| 5 | 1 | 5 | 0 | 100% | 0 | 28 | 1 | 96% |

Enforcement Ratio — доля закрытых инцидентов, у которых барьер на уровне хука, сервера или ОС, а не текста.

## Барьеры

Блок — ошибка, которая не дошла до кода. Вопрос — цена для человека: барьер, который часто спрашивает, а человек всегда разрешает, — ложное срабатывание, его надо ослабить.

| Барьер | Что | Блоков | Вопросов | | Последнее |
|---|---|---|---|---|---|
| B21 | regex across lines | 2 | 0 | ████████████████████ | 2026-11-05 |
| B27 | script without exec bit | 1 | 0 | ██████████ | 2026-11-05 |
| B24 | dependency without major bound | 1 | 0 | ██████████ | 2026-11-05 |
| B26 | CRLF in shell script | 1 | 0 | ██████████ | 2026-11-05 |

## По неделям

| Неделя | hook | git-hook | gate | tool | manual | Всего |
|---|---|---|---|---|---|---|
| 2026-W45 | 0 | 0 | 5 | 0 | 0 | 5 |

## Повторы за 7 дней

Барьер останавливает ошибку, но агент продолжает её делать. Это кандидат в инцидент: исправьте инструкцию или скилл, который ведёт агента к этой ошибке.

Повторов нет.

## Инциденты

| Уровень барьера | Инцидентов |
|---|---|
| hook | 25 |
| server | 1 |
| без уровня | 1 |
| text | 1 |

| Класс | Инцидентов |
|---|---|
| portability | 9 |
| repeat | 6 |
| tooling | 5 |
| secret leak | 4 |
| noise in statistics | 3 |
| barrier too narrow | 3 |
| encoding | 2 |
| race | 1 |
| dependency | 1 |
| performance | 1 |
| false positive | 1 |
| cost | 1 |
| false confidence | 1 |
| expected failure | 1 |
| leak | 1 |
| measurement | 1 |
| false result | 1 |
| work lost | 1 |
| no barrier possible at the hook level | 1 |

| ID | Что | Статус | Уровень | Барьеры |
|---|---|---|---|---|
| INC-2026-11-05-01 | re.M pattern read the next line in error.md | closed | hook | B21 |
| INC-2026-11-05-02 | the same re.M error in the ADR field parser | closed | hook | B21 |
| INC-2026-11-05-03 | subprocess "bash" started WSL on Windows | closed | hook | B22 |
| INC-2026-11-05-04 | the MCP selftest closed stdin before the server answered | closed | hook | B23 |
| INC-2026-11-05-05 | mcp 2.x removed the import that the server used | closed | hook | B24 |
| INC-2026-11-05-06 | Cyrillic in a heredoc reached Python as mojibake | closed | hook | B25 |
| INC-2026-11-05-07 | scripts lost the exec bit on Windows | closed | hook | B26 B27 |
| INC-2026-11-05-08 | the demo counted its own reset as 26 force pushes | closed | server |  |
| INC-2026-11-06-01 | hooks added 2.5 seconds to each tool call | closed | hook |  |
| INC-2026-11-06-02 | write_text wrote CRLF on Windows | closed | hook | B25 |
| INC-2026-11-06-03 | backslashes in heredoc and sed broke patch scripts four time | closed | hook | B38 |
| INC-2026-11-06-04 | the pack was tied to projects and cost more than it gave | closed | hook |  |
| INC-2026-11-06-05 | Git Bash rewrote a "/path" argument for Windows Python | closed | hook |  |
| INC-2026-11-06-06 | the demo counted "file not found" as a working barrier | closed | hook |  |
| INC-2026-11-06-07 | three different node errors had one signature | closed | hook |  |
| INC-2026-11-06-08 | a long heredoc broke the shell quotes, again | closed | hook | B38 |
| INC-2026-11-06-09 | the agent read files that do not exist | accepted |  |  |
| INC-2026-11-06-10 | the signature took a success line | closed | hook |  |
| INC-2026-11-06-11 | a GitLab token reached the session transcript through an err | open | hook | B07 |
| INC-2026-11-06-12 | B22 stopped the case, not the class | closed | hook | B22 |
| INC-2026-11-06-13 | sed changed "\n" into a real line break in Python code, agai | closed | hook | B38 |
| INC-2026-11-07-01 | a heredoc patch lost one level of escapes, the third time | closed | hook | B38 |
| INC-2026-11-07-02 | a relative run folder made q07 fail 10 of 10 in the first re | closed | hook |  |
| INC-2026-11-09-01 | the agent read .env through a glob, and B06 let it pass | closed | hook | B06 |
| INC-2026-11-09-02 | the agent moved the work of the user out of the repository a | closed | text |  |
| INC-2026-11-09-03 | a python -c patch lost one level of escapes, the fifth time | closed | hook | B38 |
| INC-2026-11-09-04 | a failed test printed the API key from .env into the context | closed | hook | B39 |
| INC-2026-11-09-05 | the agent read a password from config/settings.local.json | closed | hook | B06 B33 B39 |
