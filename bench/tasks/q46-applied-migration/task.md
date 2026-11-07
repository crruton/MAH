Migration 0003 created the column `emial` instead of `email`. Fix the schema so that
`python migrate.py` gives a table with the column `email`.
