FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

COPY src/hemanalyzer /app/hemanalyzer

ENV PYTHONPATH=/app

CMD ["poetry", "run", "hemanalyzer"]