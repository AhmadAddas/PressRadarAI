FROM python:3.13.15-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade --yes && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system pressradar && \
    useradd --system --gid pressradar pressradar

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade 'setuptools>=78.1.1' && \
    pip install --no-cache-dir .

FROM base AS development
RUN pip install --no-cache-dir '.[dev]'
COPY tests ./tests
CMD ["uvicorn", "pressradar.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
USER pressradar
CMD ["uvicorn", "pressradar.main:app", "--host", "0.0.0.0", "--port", "8000"]
