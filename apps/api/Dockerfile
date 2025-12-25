FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir -U uv

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock

RUN uv sync --frozen

COPY src /app/src
ENV PYTHONPATH=/app/src

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]