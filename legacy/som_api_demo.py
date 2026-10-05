"""
som_api_demo.py

API demo simplificada del proceso eTOM "Order Handling" (Process Identifier
1.1.1.5), inspirada en el tipo de recurso gestionado por un sistema real de
Service Order Management (SOM), y alineada conceptualmente -- sin pretender
conformidad ni certificacion -- con el API abierto TM Forum TMF641.

Implementa exactamente lo definido en:
  - Contrato_Datos_OrdenServicio_DuocUC.md
  - Contrato_Operativo_OrdenServicio_DuocUC.md (version 1.3)

Desde la version 1.3 del Contrato Operativo, el servicio tambien incluye:
  - Autenticacion por canal (dos claves: GUI y CRM, Seccion 4).
  - Notificaciones asincronas (webhook) de cambio de estado, con registro
    de receptor, entrega no bloqueante y conciliacion de fallos (Seccion 6).

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask jsonschema requests
Ejecucion:    python som_api_demo.py
Acceso:       http://localhost:8081/api/v1/ordenes
              http://<IP_DE_ESTE_EQUIPO>:8081/api/v1/ordenes
"""

import os
import threading
import uuid
from datetime import datetime, timezone
from functools import wraps

import requests
from flask import Flask, g, has_request_context, jsonify, request
from jsonschema import ValidationError, validate
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# 1. Configuracion -- Contrato Operativo, Secciones 3, 4 y 6
# ---------------------------------------------------------------------------

# Mapa de claves por canal -- Contrato Operativo, Seccion 4 (v1.3). La clave
# del canal GUI es la clave unica y compartida que existia antes de la
# version 1.3; se conserva sin cambios (cambio aditivo, no rompe clientes
# existentes). La clave del canal CRM es nueva.
API_KEYS = {
    "DUOC-CUY6142-DEMO": "GUI",
    "DUOC-CUY6142-DEMO-CRM": "CRM",
}

# Secreto de la solicitud saliente del webhook -- Contrato Operativo,
# Seccion 6.6. Unico y fijo, compartido por todo el curso; no es una firma
# HMAC del cuerpo, es comparacion directa de secreto compartido.
WEBHOOK_SECRET = "DUOC-CUY6142-DEMO-WEBHOOK-SECRET"

# Timeout de la solicitud saliente del webhook -- Contrato Operativo,
# Seccion 6.4. Sin reintentos automaticos: un solo intento, con este limite.
WEBHOOK_TIMEOUT_SEGUNDOS = 3

PORT = int(os.environ.get("PORT", 8081))
LOG_FILE = "som_api_demo.log"

TIPOS_SERVICIO_VALIDOS = ["INTERNET", "TELEFONIA", "TV"]
PRIORIDADES_VALIDAS = ["ALTA", "MEDIA", "BAJA"]
ESTADOS_VALIDOS = ["RECIBIDA", "EN_PROGRESO", "COMPLETADA", "CANCELADA"]

# Schema jsonschema -- traduccion directa de la tabla "Definicion del Recurso"
# del Contrato de Datos, Seccion 3. Se usa tanto en creacion (POST) como en
# reemplazo completo (PUT).
#
# No se restringe con "additionalProperties": False a proposito: el Contrato
# de Datos, Seccion 4, establece que los campos de solo lectura (id, estado,
# fecha_creacion, fecha_actualizacion) se IGNORAN si el cliente los envia, no
# se rechazan. Si aqui se pusiera additionalProperties en False, cualquier
# cliente que incluyera esos campos recibiria un 422 -- contradiciendo lo ya
# documentado en la ficha.
ORDEN_SCHEMA = {
    "type": "object",
    "properties": {
        "cliente_id": {"type": "string", "minLength": 1},
        "tipo_servicio": {"type": "string", "enum": TIPOS_SERVICIO_VALIDOS},
        "prioridad": {"type": "string", "enum": PRIORIDADES_VALIDAS},
        "descripcion": {"type": "string"},
    },
    "required": ["cliente_id", "tipo_servicio"],
}

# Schema para el cuerpo de PATCH -- solo transiciona estado (Contrato
# Operativo, Seccion 5: PATCH esta acotado a esta unica operacion).
TRANSICION_SCHEMA = {
    "type": "object",
    "properties": {
        "estado": {"type": "string", "enum": ESTADOS_VALIDOS},
    },
    "required": ["estado"],
}

# Schema para el registro de webhook -- Contrato Operativo, Seccion 6.2.
WEBHOOK_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "minLength": 1},
    },
    "required": ["url"],
}

# ---------------------------------------------------------------------------
# 2. Maquina de estados -- Contrato de Datos, Seccion 5
# ---------------------------------------------------------------------------

TRANSICIONES_VALIDAS = {
    "RECIBIDA": ["EN_PROGRESO", "CANCELADA"],
    "EN_PROGRESO": ["COMPLETADA", "CANCELADA"],
    "COMPLETADA": [],
    "CANCELADA": [],
}

ESTADOS_TERMINALES = ["COMPLETADA", "CANCELADA"]

# ---------------------------------------------------------------------------
# 3. Almacenamiento en memoria -- Contrato Operativo, Seccion 10 (exclusion
#    de persistencia declarada: se reinicia al reiniciar el proceso). Aplica
#    a las ordenes, al webhook registrado y al historial de fallos.
# ---------------------------------------------------------------------------

ordenes = {}

# Un unico webhook activo por servicio -- Contrato Operativo, Seccion 6.2.
# Registrar uno nuevo reemplaza al anterior; no se acumulan suscriptores.
webhook_registrado = {"url": None}

# Historial de intentos de entrega fallidos -- Contrato Operativo,
# Seccion 6.7. Es el mecanismo de conciliacion, dado que no hay reintentos
# automaticos de entrega.
webhooks_fallidos = []

# ---------------------------------------------------------------------------
# 4. Registro (logging) -- consola + archivo LOG_FILE.
#    Exito: [fecha] METODO RUTA -> CODIGO | canal=CANAL
#    Error: [fecha] METODO RUTA -> CODIGO | canal=CANAL | ERROR: codigo - mensaje
#    El archivo se acumula entre ejecuciones -- a diferencia del
#    almacenamiento de ordenes en memoria, que se reinicia con el proceso.
# ---------------------------------------------------------------------------


def registrar(metodo, ruta, codigo_http, error_obj=None, canal_origen=None):
    """Registra un evento en consola y en LOG_FILE.

    canal_origen -- Contrato Operativo, Seccion 4: se registra en TODAS las
    operaciones, no solo las que disparan webhook. Por defecto se resuelve
    automaticamente desde el contexto de la solicitud actual
    (g.canal_origen, fijado por requiere_api_key). El unico llamador que lo
    pasa explicitamente es el hilo de entrega de webhooks
    (_entregar_webhook), que corre fuera del contexto de solicitud de
    Flask y por lo tanto no puede leerlo de g.
    """
    if canal_origen is None and has_request_context():
        canal_origen = getattr(g, "canal_origen", None)

    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca_tiempo}] {metodo} {ruta} -> {codigo_http}"
    if canal_origen is not None:
        linea += f" | canal={canal_origen}"
    if error_obj is not None:
        linea += f" | ERROR: {error_obj['codigo']} - {error_obj['mensaje']}"

    print(linea)
    with open(LOG_FILE, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(linea + "\n")


# ---------------------------------------------------------------------------
# 5. Formato de error estandarizado -- Contrato Operativo, Seccion 7.
#    Unica fuente: alimenta tanto la respuesta al cliente como el log, para
#    que nunca queden desincronizados.
# ---------------------------------------------------------------------------


def responder_error(codigo_http, codigo, mensaje):
    error_obj = {"codigo": codigo, "mensaje": mensaje}
    registrar(request.method, request.path, codigo_http, error_obj=error_obj)
    return jsonify({"error": error_obj}), codigo_http


# ---------------------------------------------------------------------------
# 6. Autenticacion -- Contrato Operativo, Seccion 4 (v1.3). El header
#    X-API-Key ahora se valida contra un mapa de claves por canal, no contra
#    un unico valor. El canal resuelto (GUI o CRM) se guarda en g.canal_origen
#    para el resto de la solicitud -- lo usan tanto registrar() como el
#    payload del webhook (Seccion 7 de este archivo). El decorator se
#    ejecuta antes que la funcion de la ruta, y por lo tanto antes de leer
#    el cuerpo de la solicitud.
# ---------------------------------------------------------------------------


def requiere_api_key(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        clave_recibida = request.headers.get("X-API-Key")
        canal = API_KEYS.get(clave_recibida)
        if canal is None:
            return responder_error(
                401, "NO_AUTORIZADO", "Header X-API-Key ausente o incorrecto"
            )
        g.canal_origen = canal
        return func(*args, **kwargs)
    return envoltura


# ---------------------------------------------------------------------------
# 7. Webhooks -- Contrato Operativo, Seccion 6. Registro del receptor,
#    disparo no bloqueante ante cambio de estado, entrega con secreto
#    compartido, y manejo de fallos como mecanismo de conciliacion.
# ---------------------------------------------------------------------------


def disparar_webhook(orden_id, estado_anterior, estado_nuevo, operacion):
    """Dispara, en un hilo separado, la notificacion asincrona de cambio de
    estado -- Contrato Operativo, Seccion 6.3 y 6.4. No bloquea la respuesta
    de PATCH/DELETE al llamador original: el hilo se lanza y la funcion
    retorna de inmediato, sin esperar el resultado de la entrega.

    Debe llamarse dentro del contexto de la solicitud original (usa
    g.canal_origen), nunca desde el propio hilo de entrega.

    Devuelve True si habia un webhook registrado y se encolo el intento de
    entrega (el resultado, exito o fallo, se conoce despues, de forma
    asincrona -- ver Seccion 6.7); False si no hay ningun webhook
    registrado y por lo tanto no hay nada que disparar.
    """
    url_destino = webhook_registrado["url"]
    if url_destino is None:
        return False

    canal_origen = g.canal_origen
    payload = {
        "evento": "cambio_estado",
        "orden_id": orden_id,
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "operacion": operacion,
        "canal_origen": canal_origen,
        "fecha_evento": ahora_iso(),
    }

    hilo = threading.Thread(
        target=_entregar_webhook,
        args=(url_destino, payload, orden_id, operacion, canal_origen),
        daemon=True,
    )
    hilo.start()
    return True


def _entregar_webhook(url_destino, payload, orden_id, operacion, canal_origen):
    """Ejecuta el intento de entrega del webhook. Corre en un hilo separado,
    fuera del contexto de solicitud de Flask -- por eso canal_origen llega
    como argumento explicito (capturado antes de lanzar el hilo) en vez de
    leerse de g, y por eso se pasa explicitamente a registrar() aqui.

    Sin reintentos automaticos (Contrato Operativo, Seccion 6.4): un solo
    intento, con timeout corto. Cualquier fallo -- timeout, conexion
    rechazada, o codigo de respuesta fuera del rango 2xx -- se registra
    como entrega fallida (Seccion 6.7).
    """
    try:
        respuesta = requests.post(
            url_destino,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": WEBHOOK_SECRET,
            },
            timeout=WEBHOOK_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.RequestException as excepcion:
        _registrar_fallo_webhook(
            orden_id, operacion, canal_origen, url_destino, str(excepcion)
        )
        return

    if 200 <= respuesta.status_code < 300:
        registrar("WEBHOOK", url_destino, respuesta.status_code, canal_origen=canal_origen)
    else:
        _registrar_fallo_webhook(
            orden_id, operacion, canal_origen, url_destino,
            f"El receptor respondio con codigo {respuesta.status_code}",
        )


def _registrar_fallo_webhook(orden_id, operacion, canal_origen, url_destino, motivo):
    """Guarda un intento de entrega fallido -- Contrato Operativo,
    Seccion 6.7. Queda disponible via GET /api/v1/webhooks/fallos y tambien
    se escribe en el log del proceso; es el mecanismo de conciliacion, dado
    que no hay reintentos automaticos.
    """
    fallo = {
        "orden_id": orden_id,
        "operacion": operacion,
        "canal_origen": canal_origen,
        "url_destino": url_destino,
        "motivo": motivo,
        "fecha_intento": ahora_iso(),
    }
    webhooks_fallidos.append(fallo)
    registrar(
        "WEBHOOK",
        url_destino,
        "FALLO",
        error_obj={"codigo": "ENTREGA_WEBHOOK_FALLIDA", "mensaje": motivo},
        canal_origen=canal_origen,
    )


# ---------------------------------------------------------------------------
# 8. App Flask y funciones de apoyo
# ---------------------------------------------------------------------------

app = Flask(__name__)


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def orden_publica(orden):
    """Representacion completa del recurso -- Contrato de Datos, Seccion 3."""
    return {
        "id": orden["id"],
        "cliente_id": orden["cliente_id"],
        "tipo_servicio": orden["tipo_servicio"],
        "prioridad": orden["prioridad"],
        "descripcion": orden["descripcion"],
        "estado": orden["estado"],
        "fecha_creacion": orden["fecha_creacion"],
        "fecha_actualizacion": orden["fecha_actualizacion"],
    }


def obtener_json_o_error():
    """Devuelve (datos, None) si el cuerpo es JSON valido, o (None, respuesta_error)
    si no lo es -- Contrato Operativo, Seccion 7, codigo 400.

    request.get_json(silent=True) tambien devuelve None si falta el header
    Content-Type: application/json, lo cual es correcto: ese header es
    obligatorio segun el Contrato Operativo, Seccion 7.
    """
    datos = request.get_json(silent=True)
    if datos is None:
        return None, responder_error(
            400, "JSON_INVALIDO", "El cuerpo debe ser JSON valido con Content-Type: application/json"
        )
    return datos, None


# --- POST /api/v1/ordenes ---------------------------------------------------

@app.route("/api/v1/ordenes", methods=["POST"])
@requiere_api_key
def crear_orden():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    try:
        validate(instance=datos, schema=ORDEN_SCHEMA)
    except ValidationError as excepcion:
        return responder_error(422, "SCHEMA_INVALIDO", excepcion.message)

    id_orden = str(uuid.uuid4())
    marca = ahora_iso()
    orden = {
        "id": id_orden,
        "cliente_id": datos["cliente_id"],
        "tipo_servicio": datos["tipo_servicio"],
        "prioridad": datos.get("prioridad", "MEDIA"),
        "descripcion": datos.get("descripcion", ""),
        "estado": "RECIBIDA",
        "fecha_creacion": marca,
        "fecha_actualizacion": marca,
    }
    ordenes[id_orden] = orden

    registrar(request.method, request.path, 201)
    return jsonify(orden_publica(orden)), 201


# --- GET /api/v1/ordenes ----------------------------------------------------

@app.route("/api/v1/ordenes", methods=["GET"])
@requiere_api_key
def listar_ordenes():
    resultado = [orden_publica(orden) for orden in ordenes.values()]
    registrar(request.method, request.path, 200)
    return jsonify(resultado), 200


# --- GET /api/v1/ordenes/<id_orden> -----------------------------------------

@app.route("/api/v1/ordenes/<id_orden>", methods=["GET"])
@requiere_api_key
def obtener_orden(id_orden):
    orden = ordenes.get(id_orden)
    if orden is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    registrar(request.method, request.path, 200)
    return jsonify(orden_publica(orden)), 200


# --- PUT /api/v1/ordenes/<id_orden> -----------------------------------------

@app.route("/api/v1/ordenes/<id_orden>", methods=["PUT"])
@requiere_api_key
def reemplazar_orden(id_orden):
    orden = ordenes.get(id_orden)
    if orden is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    if orden["estado"] in ESTADOS_TERMINALES:
        return responder_error(
            409, "ORDEN_EN_ESTADO_TERMINAL",
            f"No se puede modificar una orden en estado {orden['estado']}"
        )

    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    try:
        validate(instance=datos, schema=ORDEN_SCHEMA)
    except ValidationError as excepcion:
        return responder_error(422, "SCHEMA_INVALIDO", excepcion.message)

    orden["cliente_id"] = datos["cliente_id"]
    orden["tipo_servicio"] = datos["tipo_servicio"]
    orden["prioridad"] = datos.get("prioridad", "MEDIA")
    orden["descripcion"] = datos.get("descripcion", "")
    orden["fecha_actualizacion"] = ahora_iso()

    registrar(request.method, request.path, 200)
    return jsonify(orden_publica(orden)), 200


# --- PATCH /api/v1/ordenes/<id_orden> ---------------------------------------

@app.route("/api/v1/ordenes/<id_orden>", methods=["PATCH"])
@requiere_api_key
def transicionar_orden(id_orden):
    orden = ordenes.get(id_orden)
    if orden is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    try:
        validate(instance=datos, schema=TRANSICION_SCHEMA)
    except ValidationError as excepcion:
        return responder_error(422, "SCHEMA_INVALIDO", excepcion.message)

    estado_actual = orden["estado"]
    estado_solicitado = datos["estado"]

    if estado_solicitado not in TRANSICIONES_VALIDAS.get(estado_actual, []):
        return responder_error(
            409, "TRANSICION_INVALIDA",
            f"No se puede pasar de {estado_actual} a {estado_solicitado}"
        )

    orden["estado"] = estado_solicitado
    orden["fecha_actualizacion"] = ahora_iso()

    hay_webhook = disparar_webhook(id_orden, estado_actual, estado_solicitado, "PATCH")

    registrar(request.method, request.path, 200)

    respuesta = orden_publica(orden)
    if hay_webhook:
        respuesta["notificacion_webhook"] = "pendiente"
    return jsonify(respuesta), 200


# --- DELETE /api/v1/ordenes/<id_orden> --------------------------------------

@app.route("/api/v1/ordenes/<id_orden>", methods=["DELETE"])
@requiere_api_key
def cancelar_orden(id_orden):
    orden = ordenes.get(id_orden)
    if orden is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    if orden["estado"] in ESTADOS_TERMINALES:
        return responder_error(
            409, "ORDEN_EN_ESTADO_TERMINAL",
            f"No se puede cancelar una orden en estado {orden['estado']}"
        )

    estado_anterior = orden["estado"]
    orden["estado"] = "CANCELADA"
    orden["fecha_actualizacion"] = ahora_iso()

    hay_webhook = disparar_webhook(id_orden, estado_anterior, "CANCELADA", "DELETE")

    registrar(request.method, request.path, 200)

    respuesta = orden_publica(orden)
    if hay_webhook:
        respuesta["notificacion_webhook"] = "pendiente"
    return jsonify(respuesta), 200


# --- POST /api/v1/webhooks --------------------------------------------------

@app.route("/api/v1/webhooks", methods=["POST"])
@requiere_api_key
def registrar_webhook():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    try:
        validate(instance=datos, schema=WEBHOOK_SCHEMA)
    except ValidationError as excepcion:
        return responder_error(422, "SCHEMA_INVALIDO", excepcion.message)

    webhook_registrado["url"] = datos["url"]

    registrar(request.method, request.path, 201)
    return jsonify({"url": webhook_registrado["url"]}), 201


# --- GET /api/v1/webhooks/fallos --------------------------------------------

@app.route("/api/v1/webhooks/fallos", methods=["GET"])
@requiere_api_key
def listar_webhooks_fallidos():
    registrar(request.method, request.path, 200)
    return jsonify(webhooks_fallidos), 200


# ---------------------------------------------------------------------------
# 9. Manejador generico de errores no controlados
# ---------------------------------------------------------------------------

@app.errorhandler(Exception)
def manejar_error_no_controlado(excepcion):
    if isinstance(excepcion, HTTPException):
        return excepcion
    return responder_error(500, "ERROR_INTERNO", "Fallo no controlado del servidor")


# ---------------------------------------------------------------------------
# 10. Arranque
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"SOM API Demo escuchando en el puerto {PORT}")
    print(f"Acceso local:  http://localhost:{PORT}/api/v1/ordenes")
    print(f"Acceso en red: http://<IP_DE_ESTE_EQUIPO>:{PORT}/api/v1/ordenes")
    print(f"Log de eventos: {LOG_FILE}")
    app.run(host="0.0.0.0", port=PORT)
