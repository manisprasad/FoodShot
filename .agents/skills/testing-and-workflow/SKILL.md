---
name: testing-and-workflow
description: Guidelines for testing (mocking async context managers, httpx responses) and git staging in this project.
---

# Testing and Workflow Guidelines

Use this skill when writing tests (specifically when mocking SQLAlchemy or httpx clients) or committing files in this repository.

## Instructions

### 1. Mocking Async Context Managers (SQLAlchemy AsyncSession)
When mocking async database context managers (like SQLAlchemy's `AsyncSession`), always configure `__aenter__.return_value = mock_session`. This ensures that assertions like `mock_session.commit.assert_called_once()` or `.rollback()` target the correct bound object inside the middleware/handler:
```python
session = AsyncMock()
session.__aenter__.return_value = session
session_pool = MagicMock()
session_pool.return_value = session
```

### 2. Mocking HTTP Responses (httpx)
When mocking responses from `httpx` async calls:
- Use `MagicMock` for the response object itself (since methods like `response.json()` and `response.raise_for_status()` are synchronous in `httpx`).
- Do NOT use `AsyncMock` for the response object, as it will cause `response.json()` to return a coroutine, leading to `AttributeError` or `TypeError`.
- Use `AsyncMock` only for the client get/post calls:
```python
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.json.return_value = {"key": "value"}
mock_get.return_value = mock_response
```

### 3. Plan Files in the Workspace
All planning documents must be saved in `doc/plans/` without providing `ArtifactMetadata` to `write_to_file`. `ArtifactMetadata` is reserved for UI-facing markdown files inside the brain directory.

### 4. Git Staging
Always stage specific files (`git add path/to/file.py`) rather than using `git add .` to avoid committing unwanted scratch files or git-ignored plan folders.

### 5. Documentation Structure & Maintenance
Maintain the `doc/` directory with strict organization:
- `doc/plans/`: Contains active and completed step-by-step task plans. Folder naming: `XX_description/`. File naming: `[X.Y]_description.md`. Statuses: `PROPOSED`, `IN PROGRESS`, `DONE`. Always mark completed plans as `DONE` at task completion.
- `doc/security/`: Dedicated directory for audits, vulnerabilities, and technical debt. Folder naming: `XX_category/`. File naming: `[X.Y]_description.md`. Maintain and update checklists when vulnerabilities are verified or fixed.
- `doc/roadmap/`: Future strategic plans and pivot documents.
- `doc/marketing/`: Drafts, blog posts, and articles.
- Root `doc/`: Keep only core documentation (`MVP.md`, `links.md`, architecture diagrams).
