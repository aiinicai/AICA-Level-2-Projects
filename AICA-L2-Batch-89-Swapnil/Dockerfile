# MCA Compliance Mapper — container image (brief §3 packaging option c).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    NO_BROWSER=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the application (no .venv, instance/, .env or tests-cache ever enter the image)
COPY app ./app
COPY engine ./engine
COPY rulepack ./rulepack
COPY migrations ./migrations
COPY alembic.ini cli.py run.py demo_data.py ./

RUN useradd --create-home appuser && mkdir -p /app/instance && chown -R appuser /app
USER appuser

EXPOSE 5000
VOLUME ["/app/instance"]

# Migrate, load the fictitious demo firm only into an empty database, then serve.
CMD ["sh", "-c", "python cli.py init-db && python cli.py seed-demo --if-empty && python run.py"]
