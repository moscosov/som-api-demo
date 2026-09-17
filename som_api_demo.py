"""
som_api_demo.py

API demo simplificada del proceso eTOM "Order Handling" (Process Identifier
1.1.1.5), inspirada en el tipo de recurso gestionado por un sistema real de
Service Order Management (SOM), y alineada conceptualmente -- sin pretender
conformidad ni certificacion -- con el API abierto TM Forum TMF641.

Implementa exactamente lo definido en:
  - Contrato_Datos_OrdenServicio_DuocUC.md
  - Contrato_Operativo_OrdenServicio_DuocUC.md

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask jsonschema
Ejecucion:    python som_api_demo.py
Acceso:       http://localhost:8081/api/v1/ordenes
              http://<IP_DE_ESTE_EQUIPO>:8081/api/v1/ordenes
"""

import os
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify
from jsonschema import validate, ValidationError
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# 1. Configuracion -- Contrato Operativo, Seccion 3 y 4
# ---------------------------------------------------------------------------

API_KEY = "DUOC-CUY6142-DEMO"
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
# 3. Almacenamiento en memoria -- Contrato Operativo, Seccion 9 (exclusion de
#    persistencia declarada: se reinicia al reiniciar el proceso)
# ---------------------------------------------------------------------------

ordenes = {}

# ---------------------------------------------------------------------------
# 4. Registro (logging) -- consola + archivo LOG_FILE.
#    Exito: [fecha] METODO RUTA -> CODIGO
#    Error: [fecha] METODO RUTA -> CODIGO | ERROR: codigo - mensaje
#    El archivo se acumula entre ejecuciones -- a diferencia del
#    almacenamiento de ordenes en memoria, que se reinicia con el proceso.
# ---------------------------------------------------------------------------

def registrar(metodo, ruta, codigo_http, error_obj=None):
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca_tiempo}] {metodo} {ruta} -> {codigo_http}"
    if error_obj is not None:
        linea += f" | ERROR: {error_obj['codigo']} - {error_obj['mensaje']}"

    print(linea)
    with open(LOG_FILE, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(linea + "\n")


# ---------------------------------------------------------------------------
# 5. Formato de error estandarizado -- Contrato Operativo, Seccion 6.
#    Unica fuente: alimenta tanto la respuesta al cliente como el log, para
#    que nunca queden desincronizados.
# ---------------------------------------------------------------------------

def responder_error(codigo_http, codigo, mensaje):
    error_obj = {"codigo": codigo, "mensaje": mensaje}
    registrar(request.method, request.path, codigo_http, error_obj)
    return jsonify({"error": error_obj}), codigo_http


# ---------------------------------------------------------------------------
# 6. Autenticacion -- Contrato Operativo, Seccion 4. Se valida antes de leer
#    el cuerpo de la solicitud (el decorator se ejecuta antes que la funcion
#    de la ruta).
# ---------------------------------------------------------------------------

def requiere_api_key(func):
    @wraps(func)
    def envoltura(*args, **kwargs):
        clave_recibida = request.headers.get("X-API-Key")
        if clave_recibida != API_KEY:
            return responder_error(
                401, "NO_AUTORIZADO", "Header X-API-Key ausente o incorrecto"
            )
        return func(*args, **kwargs)
    return envoltura


# ---------------------------------------------------------------------------
# 7. App Flask y funciones de apoyo
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
    obligatorio segun el Contrato Operativo, Seccion 6.
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
    # 404 y el chequeo de estado terminal no dependen del cuerpo de la
    # solicitud, asi que se resuelven antes de parsear/validar el JSON --
    # evita procesar un cuerpo cuando la operacion ya es invalida por si
    # misma. Contrato Operativo, Seccion 5 (nota PUT vs PATCH) y Seccion 7.
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

    # PUT reemplaza completamente los campos editables -- Contrato de Datos,
    # Seccion 4. id, estado y fecha_creacion nunca se tocan aqui.
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

    # Regla de negocio -- Contrato de Datos, Seccion 5. Valida como dato
    # (paso el schema), invalida como transicion.
    if estado_solicitado not in TRANSICIONES_VALIDAS.get(estado_actual, []):
        return responder_error(
            409, "TRANSICION_INVALIDA",
            f"No se puede pasar de {estado_actual} a {estado_solicitado}"
        )

    orden["estado"] = estado_solicitado
    orden["fecha_actualizacion"] = ahora_iso()

    registrar(request.method, request.path, 200)
    return jsonify(orden_publica(orden)), 200


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

    orden["estado"] = "CANCELADA"
    orden["fecha_actualizacion"] = ahora_iso()

    registrar(request.method, request.path, 200)
    return jsonify(orden_publica(orden)), 200


# ---------------------------------------------------------------------------
# 8. Manejador generico de errores no controlados -- Contrato Operativo,
#    Seccion 7 (500 Internal Server Error).
#
#    Deja pasar sin modificar los errores propios de Flask/Werkzeug (ej. 404
#    por ruta inexistente, 405 por metodo no soportado en una ruta valida):
#    no son parte de este contrato, que solo define comportamiento para las
#    rutas y metodos explicitamente documentados en la Seccion 5.
# ---------------------------------------------------------------------------

@app.errorhandler(Exception)
def manejar_error_no_controlado(excepcion):
    if isinstance(excepcion, HTTPException):
        return excepcion
    return responder_error(500, "ERROR_INTERNO", "Fallo no controlado del servidor")


# ---------------------------------------------------------------------------
# 9. Arranque -- Contrato Operativo, Seccion 3 (accesible por localhost e IP)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"SOM API Demo escuchando en el puerto {PORT}")
    print(f"Acceso local:  http://localhost:{PORT}/api/v1/ordenes")
    print(f"Acceso en red: http://<IP_DE_ESTE_EQUIPO>:{PORT}/api/v1/ordenes")
    print(f"Log de eventos: {LOG_FILE}")
    app.run(host="0.0.0.0", port=PORT)
