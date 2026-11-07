---
name: secrets-guard
description: Use when you touch configuration, credentials or environment files. Keeps secrets out of code, logs and prompts.
---
# Secrets guard

A secret in a commit stays in the history after you delete it.

## Rules
- Do not read, write or print `.env`, keys, certificates or files in `secrets/`.
- Do not put tokens, passwords or keys in code, tests, logs or comments.
- Read secrets from environment variables. Add a placeholder to `.env.example`.
- When you find a secret in the history, tell the human. The human must rotate the secret.

## Check before you finish
1. Run `bash gates/run-all.sh`. The check-secrets gate must pass.

## Origin
The agent tried to put a token into a dialog config. Now the gate and a hook stop this.
