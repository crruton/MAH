---
name: ste-writing
description: Use when you write text that agents read: AGENTS.md, skills, rules, gate messages. Writes it in Simplified Technical English.
---
# STE writing

Agents read the rules on each task. Short, plain English uses fewer tokens and gives one meaning.

## Rules (ASD-STE100 Issue 9)
- Write a maximum of 20 words in an instruction (rule 5.1).
- Write a maximum of 25 words in a description (rule 6.3).
- Write a maximum of six sentences in a paragraph (rule 6.6).
- Write one instruction in each sentence (rule 5.2).
- Write instructions in the imperative form (rule 5.3).
- Use the active voice (rule 3.6).
- Do not use contractions (rule 4.2).
- Do not use semicolons (rule 8.1).
- Write multi-word nouns of no more than three words (rule 2.1).
- Use approved words. Write `make sure`, not `ensure`. Write `use`, not `utilize` (rule 1.1).
- Use one term for one thing (rule 1.11).

## Check before you finish
1. Run `python gates/check-ste.py <file>`.
