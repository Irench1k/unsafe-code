FROM python:3.13-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY . .

# --- Dev stage (hot-reload for development) ---
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/pip pip install watchfiles

# Generic supervisor + entrypoint, reused across projects
COPY dev-supervisor.py /usr/local/bin/dev-supervisor.py
COPY dev-entrypoint.sh /usr/local/bin/dev-entrypoint.sh
RUN chmod +x /usr/local/bin/dev-entrypoint.sh

# In dev, PID 1 is the entrypoint → supervisor → your app
ENTRYPOINT ["/usr/local/bin/dev-entrypoint.sh"]

CMD ["python", "run.py"]

# --- Prod stage (final) ---
FROM base AS prod

EXPOSE 8000

# Production command
CMD ["python", "run.py"]
