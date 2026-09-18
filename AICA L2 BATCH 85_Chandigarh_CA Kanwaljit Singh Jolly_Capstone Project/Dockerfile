FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libgomp is required by NumPy/Pandas on slim Debian images. ca-certificates is
# explicit because every runtime process talks to Supabase, Microsoft, or Codex.
# Codex uses the distribution bubblewrap binary for its Linux command sandbox.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends bubblewrap ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt

RUN addgroup --system --gid 10001 taskchecker \
    && adduser --system --uid 10001 --ingroup taskchecker --home /app taskchecker

COPY --chown=taskchecker:taskchecker . .

USER taskchecker
EXPOSE 8000

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app_standalone:app"]

