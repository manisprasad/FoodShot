FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app

COPY --chown=appuser:appuser pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY --chown=appuser:appuser . .

RUN poetry install --no-interaction --no-ansi

USER appuser

CMD ["uvicorn", "api.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
