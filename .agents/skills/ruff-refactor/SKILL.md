---
name: ruff-refactor
description: Refactors code, fixes styling issues, and ensures compliance with project guidelines using Ruff.
---

# Instructions for the `ruff-refactor` skill

This skill automates the process of refactoring code, running the Ruff linter and formatter, and verifying that the code aligns with the global project rules.

## When to trigger this skill:
- When the user asks to "refactor code", "run ruff", "clean up this file", or explicitly calls the `ruff-refactor` command.

## Steps the AI must follow:
1. **Identify Target:** If the user hasn't specified which file or folder to refactor, ask them for the target path.
2. **Run Ruff Auto-fixes:** Use the terminal to execute the following commands via Poetry:
   - `poetry run ruff check --fix <target>` (to fix linting and import issues).
   - `poetry run ruff format <target>` (to format the code to PEP-8 standards).
3. **Review & Logical Refactoring:** Ruff only fixes syntax and style. Read the contents of the target file(s) and review the logic:
   - Ensure it follows the "Async everywhere" rule (e.g., using `aiohttp`, `async SQLAlchemy`).
   - Ensure no AI hallucinations or GPT API calls are mixed into the medical math (as strictly stated in `AGENTS.md`).
   - Check if type hints are properly used throughout.
4. **Manual Corrections:** If logical refactoring is needed beyond what Ruff did, use your file editing tools to apply those changes.
5. **Report:** Provide a brief summary of what was fixed by Ruff and what logical changes (if any) you made manually.
