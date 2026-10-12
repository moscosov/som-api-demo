# crm-som v2.0 -- CUY6142 Duoc UC
# Imagen publicada como moscosov/crm-som-demo:v2.0
#
# Construccion, desde la carpeta crm/ del repositorio:
#   docker build -t moscosov/crm-som-demo:v2.0 .

# Etapa builder: instala dependencias en un entorno virtual aislado
FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv

WORKDIR /build

COPY requirements.txt .

RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# Etapa final: imagen limpia que ejecuta la aplicacion como usuario no-root
FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 1000 --create-home appuser

RUN chown appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser crm_som.py .

ENV PORT=8082
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE $PORT

# Mismo criterio que som-api: el chequeo usa Python, sin instalar curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8082/estado', timeout=3)"]

CMD ["python", "crm_som.py"]
