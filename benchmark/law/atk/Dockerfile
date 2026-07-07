FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY prismguard ./prismguard
COPY benchmark ./benchmark

RUN pip install -U pip setuptools wheel \
    && pip install -e ".[prism,seed,benchmark-law]"

CMD ["python", "-m", "benchmark.law.atk.attack_runner"]
