---
name: create-service
description: Generates boilerplate code for a new service in the FoodShot project.
---

# Instructions for the `create-service` skill

This skill automates the creation of a base structure for new services in the application.

## When to trigger this skill:
- When the user asks to "create a new service", "write a service", or explicitly calls the `create-service` command.

## Steps the AI must follow:
1. If the service name is not provided in the user's prompt, ask for it (e.g., "What should we name the new service?").
2. Create a file `services/<service_name>.py` (for simple services) or a folder `services/<service_name>/` containing `__init__.py` and `service.py` (if the logic is expected to be complex).
3. Write the base service class. Mandatory code requirements:
   - Use asynchronous methods (following the "Async everywhere" rule).
   - Add operation logging (via `import logging` or the project's built-in logger).
   - If the service interacts with the DB, strictly use async SQLAlchemy.
   - Use Python type hints for all methods and arguments.
4. Output a brief success message to the user, along with a short example of how to import and use this new service in bot handlers (FastAPI / aiogram).
