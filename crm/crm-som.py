"""
crm_som.py

Plataforma de gestion (CRM) para la Orden de Servicio -- consume la API
som_api_demo por el canal CRM (Contrato Operativo v1.3, Seccion 4) y actua
ademas como receptor de sus notificaciones asincronas (webhook, Seccion 6).

Alcance de este canal, por decision de diseno: el CRM crea, lista, consulta,
edita (PUT) y cancela (DELETE) ordenes. No transiciona estado (PATCH) --
esa operacion queda reservada al canal GUI (Postman). Tambien recibe el
webhook de cambio de estado y refresca su vista local cuando llega, sea cual
sea el canal que origino el cambio.

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask requests
Ejecucion:    python crm_som.py
Acceso:       http://localhost:8082/
"""

import os
from datetime import datetime

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("PORT", 8082))
LOG_FILE = "crm_som.log"

# URL base de som-api. Dentro de la red Docker som-network se resuelve por
# nombre de contenedor (som-api); fuera de ella (ejecucion local sin
# Docker) se sobrescribe con la variable de entorno SOM_API_URL.
SOM_API_URL = os.environ.get("SOM_API_URL", "http://som-api:8081/api/v1")

# Clave del canal CRM -- Contrato Operativo, Seccion 4 (v1.3). Debe
# coincidir con la clave que som-api tiene registrada para ese canal.
SOM_API_KEY = os.environ.get("SOM_API_KEY", "DUOC-CUY6142-DEMO-CRM")

# Secreto esperado en las notificaciones entrantes -- Contrato Operativo,
# Seccion 6.6. Debe coincidir con el secreto configurado en som-api.
WEBHOOK_SECRET_ESPERADO = os.environ.get(
    "WEBHOOK_SECRET", "DUOC-CUY6142-DEMO-WEBHOOK-SECRET"
)

HEADERS_SOM_API = {
    "X-API-Key": SOM_API_KEY,
    "Content-Type": "application/json",
}

SOM_API_TIMEOUT_SEGUNDOS = 5

# ---------------------------------------------------------------------------
# 2. Estado local -- vista de ordenes que el CRM mantiene en memoria,
#    actualizada por las respuestas de sus propias llamadas y por los
#    webhooks entrantes. No reemplaza a som-api como fuente de verdad: es
#    una cache de lectura para la interfaz, reconciliable en cualquier
#    momento contra GET /ordenes. Se pierde al reiniciar el proceso, mismo
#    criterio de simplicidad que el estado en memoria de som-api.
# ---------------------------------------------------------------------------

ordenes_locales = {}

# ---------------------------------------------------------------------------
# 3. Registro (logging) -- mismo formato de linea que som_api_demo.py, para
#    que las evidencias de ambos servicios sean comparables lado a lado.
# ---------------------------------------------------------------------------


def registrar(evento, detalle=""):
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca_tiempo}] {evento}"
    if detalle:
        linea += f" | {detalle}"
    print(linea)
    with open(LOG_FILE, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(linea + "\n")


# ---------------------------------------------------------------------------
# 4. Cliente REST -- llamadas hacia som-api, canal CRM. Cubre las cinco
#    operaciones que son prerrogativa del CRM: crear, listar, consultar,
#    editar (PUT) y cancelar (DELETE). PATCH queda deliberadamente fuera.
# ---------------------------------------------------------------------------


def som_api_crear_orden(datos):
    return requests.post(
        f"{SOM_API_URL}/ordenes",
        json=datos,
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


def som_api_listar_ordenes():
    return requests.get(
        f"{SOM_API_URL}/ordenes",
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


def som_api_obtener_orden(id_orden):
    return requests.get(
        f"{SOM_API_URL}/ordenes/{id_orden}",
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


def som_api_editar_orden(id_orden, datos):
    return requests.put(
        f"{SOM_API_URL}/ordenes/{id_orden}",
        json=datos,
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


def som_api_cancelar_orden(id_orden):
    return requests.delete(
        f"{SOM_API_URL}/ordenes/{id_orden}",
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


# ---------------------------------------------------------------------------
# 5. App Flask -- endpoints propios del CRM. Por ahora son JSON puro (sin
#    interfaz): el esqueleto cubre el cliente REST y el receptor de
#    webhook; la interfaz (formularios, listado visual) es un paso
#    posterior, sobre esta misma base.
# ---------------------------------------------------------------------------

app = Flask(__name__)


def obtener_json_o_error():
    datos = request.get_json(silent=True)
    if datos is None:
        return None, (jsonify({"error": "El cuerpo debe ser JSON valido con Content-Type: application/json"}), 400)
    return datos, None


# --- POST /ordenes -- crear (proxy hacia som-api) ---------------------------

@app.route("/ordenes", methods=["POST"])
def crear_orden():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    respuesta = som_api_crear_orden(datos)
    if respuesta.status_code == 201:
        orden = respuesta.json()
        ordenes_locales[orden["id"]] = orden
        registrar("ORDEN_CREADA", f"id={orden['id']}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- GET /ordenes -- listar (proxy, refresca la cache local) ---------------

@app.route("/ordenes", methods=["GET"])
def listar_ordenes():
    respuesta = som_api_listar_ordenes()
    if respuesta.status_code == 200:
        for orden in respuesta.json():
            ordenes_locales[orden["id"]] = orden

    return jsonify(respuesta.json()), respuesta.status_code


# --- GET /ordenes/<id_orden> -- detalle (proxy) -----------------------------

@app.route("/ordenes/<id_orden>", methods=["GET"])
def obtener_orden(id_orden):
    respuesta = som_api_obtener_orden(id_orden)
    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()

    return jsonify(respuesta.json()), respuesta.status_code


# --- PUT /ordenes/<id_orden> -- editar (proxy) ------------------------------

@app.route("/ordenes/<id_orden>", methods=["PUT"])
def editar_orden(id_orden):
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    respuesta = som_api_editar_orden(id_orden, datos)
    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()
        registrar("ORDEN_EDITADA", f"id={id_orden}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- DELETE /ordenes/<id_orden> -- cancelar (proxy) -------------------------

@app.route("/ordenes/<id_orden>", methods=["DELETE"])
def cancelar_orden(id_orden):
    respuesta = som_api_cancelar_orden(id_orden)
    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()
        registrar("ORDEN_CANCELADA", f"id={id_orden}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- POST /webhooks/ordenes -- receptor del webhook -------------------------

@app.route("/webhooks/ordenes", methods=["POST"])
def recibir_webhook():
    """Receptor de las notificaciones asincronas de som-api -- Contrato
    Operativo, Seccion 6. Valida el secreto compartido antes de procesar
    el cuerpo (Seccion 6.6), mismo criterio que som-api aplica con
    X-API-Key en sus propios endpoints (Seccion 4).
    """
    secreto_recibido = request.headers.get("X-Webhook-Secret")
    if secreto_recibido != WEBHOOK_SECRET_ESPERADO:
        registrar("WEBHOOK_RECHAZADO", "X-Webhook-Secret ausente o incorrecto")
        return jsonify({"error": "X-Webhook-Secret ausente o incorrecto"}), 401

    evento = request.get_json(silent=True)
    if evento is None:
        return jsonify({"error": "El cuerpo debe ser JSON valido"}), 400

    orden_id = evento.get("orden_id")
    registrar(
        "WEBHOOK_RECIBIDO",
        f"orden_id={orden_id} operacion={evento.get('operacion')} "
        f"estado={evento.get('estado_anterior')}->{evento.get('estado_nuevo')} "
        f"canal_origen={evento.get('canal_origen')}",
    )

    # El payload del webhook es liviano por diseno (Contrato Operativo,
    # Seccion 6.5): no trae la representacion completa de la orden. En vez
    # de confiar en el estado_nuevo del evento para pintar la vista local,
    # se confirma con un GET a som-api -- coherente con el patron que el
    # propio contrato describe para el receptor.
    if orden_id:
        respuesta = som_api_obtener_orden(orden_id)
        if respuesta.status_code == 200:
            ordenes_locales[orden_id] = respuesta.json()

    return jsonify({"recibido": True}), 200


# --- GET / -- estado basico del servicio ------------------------------------

@app.route("/", methods=["GET"])
def estado():
    return jsonify({
        "servicio": "crm-som",
        "ordenes_en_cache": len(ordenes_locales),
        "som_api_url": SOM_API_URL,
    }), 200


# ---------------------------------------------------------------------------
# 6. Arranque -- threaded=True: crm-som puede recibir el webhook entrante
#    mientras tiene una llamada saliente en curso hacia som-api (por
#    ejemplo, un DELETE esperando respuesta). Sin esto, el servidor de
#    desarrollo de Flask atiende una solicitud a la vez y ambas quedarian
#    en interbloqueo -- ver la nota de diseno del webhook en el Contrato
#    Operativo, Seccion 6.4.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"crm-som escuchando en el puerto {PORT}")
    print(f"Acceso local:   http://localhost:{PORT}/")
    print(f"som-api configurada en: {SOM_API_URL}")
    print(f"Log de eventos: {LOG_FILE}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)