FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv

WORKDIR /build

COPY requirements.txt .

RUN /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 1000 --create-home appuser

RUN chown appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser som_api_demo.py .

ENV PORT=8081

ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE $PORT

CMD ["python", "som_api_demo.py"]
