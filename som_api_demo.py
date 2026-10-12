"""
som_api_demo.py -- version 2.1

API demo simplificada del proceso eTOM "Order Handling" (Process Identifier
1.1.1.5), inspirada en el tipo de recurso gestionado por un sistema real de
Service Order Management (SOM), y alineada conceptualmente -- sin pretender
conformidad ni certificacion -- con los API abiertos TM Forum TMF641
(Service Ordering), TMF638 (Service Inventory) y TMF620 (Product Catalog).

Implementa exactamente lo definido en:
  - Contrato_Datos_OrdenServicio_DuocUC.md      (version 2.0)
  - Contrato_Operativo_OrdenServicio_DuocUC.md  (version 2.1)
  - DisenoFuncional_OrdenServicio_DuocUC.md     (version 2.1)

Version 2.1: solo cambia la documentacion OpenAPI (descripciones, formatos,
valores por defecto y campos de solo lectura). El contrato y el
comportamiento de la API son los de la version 2.0.

Los comentarios citan las reglas del Contrato de Datos por su codigo
(RV-xx: reglas de schema, RN-xx: reglas de negocio) y las secciones de los
documentos. El orden de los pasos de cada ruta sigue el Diseno Funcional,
Seccion 4: ese orden define que error recibe una solicitud que viola varias
reglas a la vez.

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask jsonschema requests
Ejecucion:    python som_api_demo.py
Acceso:       http://localhost:8081/api/v2/docs
              http://<IP_DE_ESTE_EQUIPO>:8081/api/v2/docs
"""

import base64
import json
import math
import os
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from functools import wraps

import requests
from flask import Flask, Response, g, has_request_context, jsonify, request
from jsonschema import ValidationError, validate
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# 1. Configuracion -- Contrato Operativo, Secciones 3 y 4
# ---------------------------------------------------------------------------

BASE = "/api/v2"
PORT = int(os.environ.get("PORT", 8081))
LOG_FILE = "som_api_demo.log"

# Archivo de persistencia -- Contrato Operativo, Seccion 3. Ruta relativa al
# directorio de trabajo del proceso (/app/data/som_data.json en el contenedor).
DATA_FILE = os.environ.get("SOM_DATA_FILE", os.path.join("data", "som_data.json"))

# Claves fijas de canal -- Contrato Operativo, Seccion 4.3. Mismos valores de
# la version 1.3: integracion entre sistemas (por ejemplo, crm-som).
API_KEYS = {
    "DUOC-CUY6142-DEMO": "GUI",
    "DUOC-CUY6142-DEMO-CRM": "CRM",
}

# Usuarios del login con autenticacion basica -- Contrato Operativo,
# Seccion 4.2. Cada usuario pertenece a un canal.
USUARIOS = {
    "gui": {"password": "Cuy6142!", "canal": "GUI"},
    "crm": {"password": "Cuy6142!", "canal": "CRM"},
}

# Secreto de la solicitud saliente del webhook -- Contrato Operativo, Seccion 6.6.
WEBHOOK_SECRET = "DUOC-CUY6142-DEMO-WEBHOOK-SECRET"
WEBHOOK_TIMEOUT_SEGUNDOS = 3

# Valores permitidos -- Contrato de Datos, Seccion 3.6.
TIPOS_ORDEN = ["ALTA", "BAJA", "CAMBIO_OFERTA", "RELOCALIZACION"]
TIPOS_SERVICIO = ["INTERNET", "TELEFONIA", "TV"]
PRIORIDADES = ["ALTA", "MEDIA", "BAJA"]
ESTADOS_ORDEN = ["RECIBIDA", "EN_PROGRESO", "COMPLETADA", "CANCELADA"]
ESTADOS_SUSCRIPCION = ["PENDIENTE", "ACTIVA", "ANULADA", "BAJA"]
IDIOMAS = ["es", "en"]

# Prefijo de servicio de subscription_id y offer_id -- Contrato de Datos, Seccion 3.5.
PREFIJO_SERVICIO = {"INTERNET": "20", "TV": "30", "TELEFONIA": "40"}

# Catalogo vigente, fijo y de solo lectura -- Contrato de Datos, Seccion 3.4.
CATALOGO = [
    {"offer_id": "200101", "nombre": "Fibra 300 Mbps", "tipo_servicio": "INTERNET"},
    {"offer_id": "200102", "nombre": "Fibra 600 Mbps", "tipo_servicio": "INTERNET"},
    {"offer_id": "200103", "nombre": "Fibra 1 Gbps", "tipo_servicio": "INTERNET"},
    {"offer_id": "300101", "nombre": "TV Básico", "tipo_servicio": "TV"},
    {"offer_id": "300102", "nombre": "TV Premium", "tipo_servicio": "TV"},
    {"offer_id": "300103", "nombre": "TV Premium con Deportes", "tipo_servicio": "TV"},
    {"offer_id": "400101", "nombre": "Fija Local", "tipo_servicio": "TELEFONIA"},
    {"offer_id": "400102", "nombre": "Fija Nacional Ilimitada", "tipo_servicio": "TELEFONIA"},
    {"offer_id": "400103", "nombre": "Fija con Internacional", "tipo_servicio": "TELEFONIA"},
]
CATALOGO_POR_ID = {oferta["offer_id"]: oferta for oferta in CATALOGO}

# Parametros del calculo de relocalizacion -- Contrato de Datos, Seccion 4.4.
DURACION_DESCONEXION_MS = 600000   # 10 minutos
MS_POR_METRO = 120000              # 2 minutos por metro de cable
DURACION_CONEXION_MS = 900000      # 15 minutos

# Paginacion -- Contrato Operativo, Seccion 5.2.
SIZE_DEFAULT = 20
SIZE_MAXIMO = 100

# Campos inmutables de la orden -- Contrato de Datos, Seccion 3.1 (RN-13).
CAMPOS_INMUTABLES = [
    "tipo_orden", "com_id", "cliente_id", "tipo_servicio", "offer_id",
    "subscription_id", "punto_actual", "punto_destino",
]

# ---------------------------------------------------------------------------
# 2. Schemas jsonschema -- Contrato de Datos, Secciones 3 y 4.1
#
#    Un schema por tipo de orden (Diseno Funcional, Seccion 5): cada uno
#    corresponde a una columna de la tabla "Campos obligatorios por tipo de
#    orden en la creacion". No se usa additionalProperties: False en la
#    creacion porque los campos de solo lectura y los que no aplican al tipo
#    se IGNORAN, no se rechazan (RV-09, RV-10).
# ---------------------------------------------------------------------------

#    Las claves "description", "default" y "title" solo documentan: jsonschema
#    no las usa para validar. Se ven en Swagger UI (Seccion 17).

TEXTO_CATALOGO = "\n".join(
    f"- `{oferta['offer_id']}` {oferta['nombre']} ({oferta['tipo_servicio']})" for oferta in CATALOGO
)

PUNTO_SCHEMA = {
    "type": "object",
    "description": "Ubicación de un punto de red en el plano del hogar, en metros. "
                   "El eje x crece hacia el este y el eje y hacia el norte.",
    "properties": {
        "x": {"type": "number", "minimum": 0, "maximum": 100,
              "description": "Coordenada este-oeste, en metros, de 0 a 100. Admite decimales."},
        "y": {"type": "number", "minimum": 0, "maximum": 100,
              "description": "Coordenada norte-sur, en metros, de 0 a 100. Admite decimales."},
        "referencia": {"type": "string", "maxLength": 40,
                       "description": "Nombre del recinto (ej. Living), hasta 40 caracteres. "
                                      "Aparece en los textos de los pasos de trabajo."},
    },
    "required": ["x", "y"],
}

PROPIEDADES_COMUNES = {
    "tipo_orden": {"type": "string", "enum": TIPOS_ORDEN, "default": "ALTA",
                   "description": "Tipo de orden. Si se omite, se asume ALTA (RV-01)."},
    "com_id": {"type": "string", "pattern": "^[0-9]{7}$",
               "description": "Número de orden comercial del sistema que pide la orden (CRM o GUI). "
                              "Exactamente 7 dígitos, como texto, para conservar los ceros a la izquierda "
                              "(ej. \"0000005\"). Lo envía el cliente y no se puede repetir: un com_id "
                              "ya usado responde 409 COM_ID_DUPLICADO (RN-01)."},
    "cliente_id": {"type": "string", "minLength": 1,
                   "description": "Identificador del cliente: texto no vacío (RV-04). En las actividades "
                                  "del curso, el RUT sin puntos ni guion. En BAJA, CAMBIO_OFERTA y "
                                  "RELOCALIZACION debe ser el titular de la suscripción (RN-05)."},
    "tipo_servicio": {"type": "string", "enum": TIPOS_SERVICIO,
                      "description": "Servicio. Obligatorio en ALTA. En los demás tipos es opcional y, si "
                                     "se envía, debe coincidir con el servicio de la suscripción (RN-06)."},
    "prioridad": {"type": "string", "enum": PRIORIDADES, "default": "MEDIA",
                  "description": "Prioridad de la orden. Si se omite, MEDIA."},
    "descripcion": {"type": "string", "default": "",
                    "description": "Detalle libre de la solicitud. Si se omite, queda vacía."},
}
SUBSCRIPTION_ID_SCHEMA = {
    "type": "string", "pattern": "^[0-9]{8}$",
    "description": "Suscripción: exactamente 8 dígitos, como texto. Prefijo de servicio (20 INTERNET, "
                   "30 TV, 40 TELEFONIA) más un correlativo de 6 dígitos. La genera SOM al crear un ALTA. "
                   "En BAJA, CAMBIO_OFERTA y RELOCALIZACION la envía el cliente: debe existir "
                   "(404 SUSCRIPCION_NO_ENCONTRADA, RN-04) y estar ACTIVA (409 SUSCRIPCION_NO_ACTIVA, RN-07).",
}
OFFER_ID_SCHEMA = {
    "type": "string", "pattern": "^[0-9]{6}$",
    "description": "Oferta del catálogo: exactamente 6 dígitos, como texto. Prefijo de servicio (20 INTERNET, "
                   "30 TV, 40 TELEFONIA) más el número de oferta. Una oferta que no está en el catálogo "
                   "responde 404 OFERTA_NO_ENCONTRADA (RN-02); una de otro servicio, 422 "
                   "OFERTA_NO_CORRESPONDE_A_SERVICIO (RN-03). Catálogo vigente:\n\n" + TEXTO_CATALOGO,
}

SCHEMAS_CREACION = {
    "ALTA": {
        "type": "object",
        "title": "Creación de ALTA",
        "description": "Contratar un servicio. Crea una suscripción en estado PENDIENTE.",
        "properties": {**PROPIEDADES_COMUNES, "offer_id": OFFER_ID_SCHEMA},
        "required": ["com_id", "cliente_id", "tipo_servicio", "offer_id"],
    },
    "BAJA": {
        "type": "object",
        "title": "Creación de BAJA",
        "description": "Dar de baja la suscripción indicada. Requiere tipo_orden BAJA.",
        "properties": {**PROPIEDADES_COMUNES, "subscription_id": SUBSCRIPTION_ID_SCHEMA},
        "required": ["com_id", "cliente_id", "subscription_id"],
    },
    "CAMBIO_OFERTA": {
        "type": "object",
        "title": "Creación de CAMBIO_OFERTA",
        "description": "Cambiar la oferta vigente de la suscripción. Requiere tipo_orden CAMBIO_OFERTA.",
        "properties": {
            **PROPIEDADES_COMUNES,
            "subscription_id": SUBSCRIPTION_ID_SCHEMA,
            "offer_id": OFFER_ID_SCHEMA,
        },
        "required": ["com_id", "cliente_id", "subscription_id", "offer_id"],
    },
    "RELOCALIZACION": {
        "type": "object",
        "title": "Creación de RELOCALIZACION",
        "description": "Trasladar el punto de red dentro del hogar. Requiere tipo_orden RELOCALIZACION. "
                       "SOM calcula los metros de cable, la duración y los pasos del trabajo.",
        "properties": {
            **PROPIEDADES_COMUNES,
            "subscription_id": SUBSCRIPTION_ID_SCHEMA,
            "punto_actual": PUNTO_SCHEMA,
            "punto_destino": PUNTO_SCHEMA,
        },
        "required": ["com_id", "cliente_id", "subscription_id", "punto_actual", "punto_destino"],
    },
}

# Reemplazo completo (PUT) -- RV-07: prioridad y descripcion obligatorios.
REEMPLAZO_SCHEMA = {
    "type": "object",
    "description": "Reemplazo completo de los campos editables: prioridad y descripción son obligatorios "
                   "(RV-07). Si se incluye un campo inmutable, debe coincidir con su valor vigente "
                   "(409 CAMPO_INMUTABLE, RN-13).",
    "properties": {
        "prioridad": {"type": "string", "enum": PRIORIDADES, "description": "Prioridad nueva."},
        "descripcion": {"type": "string", "description": "Descripción nueva."},
    },
    "required": ["prioridad", "descripcion"],
}

# Actualizacion parcial (PATCH) -- RV-08: al menos uno de estado y
# descripcion, y ningun otro campo.
ACTUALIZACION_SCHEMA = {
    "type": "object",
    "description": "Actualización parcial: al menos uno de estado y descripción, y ningún otro campo (RV-08).",
    "properties": {
        "estado": {"type": "string", "enum": ESTADOS_ORDEN,
                   "description": "Estado nuevo. Transiciones permitidas: RECIBIDA a EN_PROGRESO, EN_PROGRESO "
                                  "a COMPLETADA, y RECIBIDA o EN_PROGRESO a CANCELADA. Otra transición "
                                  "responde 409 TRANSICION_INVALIDA (RN-11)."},
        "descripcion": {"type": "string", "description": "Descripción nueva."},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

# Registro de webhook -- Contrato Operativo, Seccion 6.2.
WEBHOOK_SCHEMA = {
    "type": "object",
    "properties": {"url": {"type": "string", "minLength": 1,
                           "description": "URL del receptor que recibirá las notificaciones de cambio de estado."}},
    "required": ["url"],
}

# ---------------------------------------------------------------------------
# 3. Maquinas de estados -- Contrato de Datos, Secciones 5.1 y 5.3
# ---------------------------------------------------------------------------

TRANSICIONES_VALIDAS = {
    "RECIBIDA": ["EN_PROGRESO", "CANCELADA"],
    "EN_PROGRESO": ["COMPLETADA", "CANCELADA"],
    "COMPLETADA": [],
    "CANCELADA": [],
}
ESTADOS_TERMINALES = ["COMPLETADA", "CANCELADA"]

# ---------------------------------------------------------------------------
# 4. Estado del servicio
#
#    - estado: ordenes, suscripciones y correlativos. Se persiste en
#      DATA_FILE (Contrato Operativo, Seccion 3).
#    - tokens, webhook y fallos: datos de sesion, solo en memoria.
#    - candado: unico candado global (Diseno Funcional, Seccion 5). Todo
#      acceso al estado compartido ocurre con el candado tomado.
# ---------------------------------------------------------------------------

estado = {
    "ordenes": {},
    "suscripciones": {},
    "correlativos": {servicio: 0 for servicio in TIPOS_SERVICIO},
}
tokens = {}
webhook_registrado = {"url": None}
webhooks_fallidos = []
candado = threading.Lock()


def cargar_estado():
    """Arranque -- Diseno Funcional, Seccion 4.1. Si el archivo existe pero
    no se puede leer o no tiene la estructura esperada, el servicio NO
    arranca: no sobrescribe un archivo que no entiende."""
    directorio = os.path.dirname(DATA_FILE)
    if directorio:
        os.makedirs(directorio, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        print(f"Archivo de datos {DATA_FILE} no existe: se inicia con estado vacio")
        return

    try:
        with open(DATA_FILE, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not (
            isinstance(datos, dict)
            and isinstance(datos.get("ordenes"), dict)
            and isinstance(datos.get("suscripciones"), dict)
            and isinstance(datos.get("correlativos"), dict)
        ):
            raise ValueError("estructura inesperada (faltan ordenes, suscripciones o correlativos)")
    except (OSError, ValueError) as excepcion:
        raise SystemExit(
            f"ERROR: no se puede cargar {DATA_FILE}: {excepcion}. "
            "Revise o elimine el archivo antes de iniciar el servicio."
        )

    estado["ordenes"] = datos["ordenes"]
    estado["suscripciones"] = datos["suscripciones"]
    for servicio in TIPOS_SERVICIO:
        estado["correlativos"][servicio] = int(datos["correlativos"].get(servicio, 0))
    print(
        f"Estado cargado desde {DATA_FILE}: {len(estado['ordenes'])} ordenes, "
        f"{len(estado['suscripciones'])} suscripciones"
    )


def guardar_estado():
    """Persistencia -- Diseno Funcional, Seccion 4.15. Escritura a un archivo
    temporal del mismo directorio y reemplazo atomico con os.replace: un
    corte durante la escritura deja intacto el archivo anterior. Se llama
    siempre con el candado tomado."""
    directorio = os.path.dirname(DATA_FILE) or "."
    descriptor, ruta_temporal = tempfile.mkstemp(dir=directorio, prefix=".som_data_", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(estado, archivo, ensure_ascii=False, indent=2)
            archivo.flush()
            os.fsync(archivo.fileno())
        # mkstemp crea el archivo con permisos 0600; se deja legible (cat).
        os.chmod(ruta_temporal, 0o644)
        os.replace(ruta_temporal, DATA_FILE)
    except OSError:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        raise


# ---------------------------------------------------------------------------
# 5. Registro (logging) -- consola + archivo LOG_FILE
#    Exito: [fecha] METODO RUTA -> CODIGO | canal=CANAL
#    Error: [fecha] METODO RUTA -> CODIGO | canal=CANAL | ERROR: codigo - mensaje
# ---------------------------------------------------------------------------


def registrar(metodo, ruta, codigo_http, error_obj=None, canal_origen=None):
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
# 6. Formato de error estandarizado -- Contrato Operativo, Seccion 7.
#    Unica fuente: alimenta la respuesta y el log.
# ---------------------------------------------------------------------------


def responder_error(codigo_http, codigo, mensaje):
    error_obj = {"codigo": codigo, "mensaje": mensaje}
    registrar(request.method, request.path, codigo_http, error_obj=error_obj)
    return jsonify({"error": error_obj}), codigo_http


def error_schema(excepcion):
    """RV-xx -> 422 SCHEMA_INVALIDO. El mensaje incluye el campo afectado y
    el texto de jsonschema, en ingles (Diseno Funcional, Seccion 6)."""
    campo = ".".join(str(parte) for parte in excepcion.absolute_path)
    mensaje = f"{campo}: {excepcion.message}" if campo else excepcion.message
    return responder_error(422, "SCHEMA_INVALIDO", mensaje)


def error_persistencia():
    """Falla de escritura del archivo -- Diseno Funcional, Seccion 7."""
    return responder_error(500, "ERROR_INTERNO", "No se pudo guardar el estado en el archivo de datos")


# ---------------------------------------------------------------------------
# 7. Aplicacion Flask
# ---------------------------------------------------------------------------

app = Flask(__name__)
# Las respuestas conservan el orden de campos del Contrato de Datos (Flask
# ordena las claves alfabeticamente por defecto) y los caracteres en espanol.
app.json.sort_keys = False
app.json.ensure_ascii = False


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def obtener_json_o_error():
    """(datos, None) si el cuerpo es JSON valido; (None, respuesta) si no.
    Sin Content-Type: application/json, get_json devuelve None: 400."""
    datos = request.get_json(silent=True)
    if datos is None:
        return None, responder_error(
            400, "JSON_INVALIDO",
            "El cuerpo debe ser JSON valido con Content-Type: application/json",
        )
    return datos, None


# ---------------------------------------------------------------------------
# 8. Autenticacion -- Contrato Operativo, Seccion 4; Diseno Funcional, 4.2
# ---------------------------------------------------------------------------


def requiere_credencial(funcion):
    """Procedimiento comun de autenticacion. Header X-API-KEY (los nombres de
    header no distinguen mayusculas) o, si no viene, parametro key. Acepta
    una clave fija de canal o un token de sesion. Resuelve canal_origen."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        credencial = request.headers.get("X-API-KEY") or request.args.get("key")
        canal = None
        if credencial:
            canal = API_KEYS.get(credencial) or tokens.get(credencial)
        if canal is None:
            return responder_error(401, "NO_AUTORIZADO", "Credencial X-API-KEY o key ausente o invalida")
        g.canal_origen = canal
        return funcion(*args, **kwargs)
    return envoltura


@app.route(f"{BASE}/loginViaBasic", methods=["POST"])
def login_via_basic():
    """Login -- Contrato Operativo, Seccion 4.2; Diseno Funcional, 4.3."""
    usuario = None
    password = None
    encabezado = request.headers.get("Authorization", "")
    # El nombre del esquema (Basic) no distingue mayusculas (RFC 7617).
    if encabezado[:6].lower() == "basic ":
        try:
            decodificado = base64.b64decode(encabezado[6:], validate=True).decode("utf-8")
            usuario, _, password = decodificado.partition(":")
        except (ValueError, UnicodeDecodeError):
            usuario = None

    datos_usuario = USUARIOS.get(usuario)
    if datos_usuario is None or not secrets.compare_digest(password or "", datos_usuario["password"]):
        respuesta, codigo = responder_error(401, "CREDENCIALES_INVALIDAS", "Usuario o contrasena incorrectos")
        respuesta.headers["WWW-Authenticate"] = 'Basic realm="SOM"'
        return respuesta, codigo

    # usuario|cadena aleatoria de 43 caracteres (32 bytes en base64 URL-safe)
    token = f"{usuario}|{secrets.token_urlsafe(32)}"
    tokens[token] = datos_usuario["canal"]
    g.canal_origen = datos_usuario["canal"]
    # El token no se escribe en el log.
    registrar(request.method, request.path, 200)
    return jsonify({"token": token}), 200


# ---------------------------------------------------------------------------
# 9. Representaciones -- Contrato de Datos, Secciones 3.1, 3.3, 3.4 y 3.7
# ---------------------------------------------------------------------------


def orden_publica(orden, incluir_oferta=False):
    """Representacion completa de la orden. Todos los campos presentes; los
    que no aplican al tipo de orden van en null (Contrato de Datos, 3.1)."""
    representacion = {
        "id": orden["id"],
        "tipo_orden": orden["tipo_orden"],
        "com_id": orden["com_id"],
        "cliente_id": orden["cliente_id"],
        "tipo_servicio": orden["tipo_servicio"],
        "offer_id": orden["offer_id"],
        "subscription_id": orden["subscription_id"],
        "punto_actual": orden["punto_actual"],
        "punto_destino": orden["punto_destino"],
        "distancia_m": orden["distancia_m"],
        "duracion_estimada_ms": orden["duracion_estimada_ms"],
        "prioridad": orden["prioridad"],
        "descripcion": orden["descripcion"],
        "estado": orden["estado"],
        "fecha_creacion": orden["fecha_creacion"],
        "fecha_actualizacion": orden["fecha_actualizacion"],
    }
    if incluir_oferta:
        # Representacion expandida: el campo oferta solo existe si se pide.
        representacion["oferta"] = CATALOGO_POR_ID.get(orden["offer_id"]) if orden["offer_id"] else None
    return representacion


def suscripcion_publica(suscripcion):
    return {
        "subscription_id": suscripcion["subscription_id"],
        "cliente_id": suscripcion["cliente_id"],
        "tipo_servicio": suscripcion["tipo_servicio"],
        "offer_id": suscripcion["offer_id"],
        "estado": suscripcion["estado"],
        "orden_alta_id": suscripcion["orden_alta_id"],
        "fecha_creacion": suscripcion["fecha_creacion"],
        "fecha_actualizacion": suscripcion["fecha_actualizacion"],
    }


def servicio_de_oferta(offer_id):
    """Servicio que indica el prefijo de un offer_id (Contrato de Datos, 3.5)."""
    for servicio, prefijo in PREFIJO_SERVICIO.items():
        if offer_id.startswith(prefijo):
            return servicio
    return None


# ---------------------------------------------------------------------------
# 10. Calculo de relocalizacion -- Contrato de Datos, Seccion 4.4;
#     Diseno Funcional, Seccion 4.14. Funcion pura y determinista.
#
#     Se usa Decimal con redondeo de mitades hacia arriba: round() de Python
#     usa redondeo bancario sobre la representacion binaria del float, y no
#     coincide con el calculo manual del estudiante.
# ---------------------------------------------------------------------------

TEXTOS_PASOS = {
    "es": {
        "desconexion": "Desconectar el equipo en el punto actual",
        "este": "Tender cable hacia el este",
        "oeste": "Tender cable hacia el oeste",
        "norte": "Tender cable hacia el norte",
        "sur": "Tender cable hacia el sur",
        "conexion": "Conectar y verificar el equipo en el punto de destino",
    },
    "en": {
        "desconexion": "Disconnect the device at the current point",
        "este": "Run cable to the east",
        "oeste": "Run cable to the west",
        "norte": "Run cable to the north",
        "sur": "Run cable to the south",
        "conexion": "Connect and test the device at the destination point",
    },
}

MILIMETRO = Decimal("0.001")
ENTERO = Decimal("1")


def numero_json(valor):
    """Decimal -> numero JSON: entero si no tiene parte decimal (0, 6),
    float en otro caso (3.625)."""
    if valor == valor.to_integral_value():
        return int(valor)
    return float(valor)


def con_referencia(texto, punto):
    referencia = punto.get("referencia")
    return f"{texto} ({referencia})" if referencia else texto


def calcular_relocalizacion(punto_actual, punto_destino, idioma="en"):
    """Devuelve (distancia_m, duracion_estimada_ms, pasos)."""
    textos = TEXTOS_PASOS[idioma]
    dx = Decimal(str(punto_destino["x"])) - Decimal(str(punto_actual["x"]))
    dy = Decimal(str(punto_destino["y"])) - Decimal(str(punto_actual["y"]))

    tramos = [(con_referencia(textos["desconexion"], punto_actual), Decimal(0), Decimal(DURACION_DESCONEXION_MS))]
    for delta, positivo, negativo in ((dx, "este", "oeste"), (dy, "norte", "sur")):
        distancia = abs(delta).quantize(MILIMETRO, rounding=ROUND_HALF_UP)
        if distancia != 0:
            duracion = (distancia * MS_POR_METRO).quantize(ENTERO, rounding=ROUND_HALF_UP)
            tramos.append((textos[positivo if delta > 0 else negativo], distancia, duracion))
    tramos.append((con_referencia(textos["conexion"], punto_destino), Decimal(0), Decimal(DURACION_CONEXION_MS)))

    pasos = [
        {
            "secuencia": numero,
            "texto": texto,
            "distancia_m": numero_json(distancia),
            "duracion_ms": int(duracion),
        }
        for numero, (texto, distancia, duracion) in enumerate(tramos, start=1)
    ]
    distancia_total = sum(distancia for _, distancia, _ in tramos).quantize(MILIMETRO, rounding=ROUND_HALF_UP)
    duracion_total = int(sum(duracion for _, _, duracion in tramos))
    return numero_json(distancia_total), duracion_total, pasos


def puntos_finitos(*puntos):
    """Complemento de RV-06: el parser JSON de Python acepta NaN e Infinity,
    que jsonschema no rechaza con minimum/maximum."""
    return all(math.isfinite(punto[eje]) for punto in puntos for eje in ("x", "y"))


def puntos_iguales(punto_actual, punto_destino):
    """RN-09: distancia cero."""
    return all(Decimal(str(punto_actual[eje])) == Decimal(str(punto_destino[eje])) for eje in ("x", "y"))


# ---------------------------------------------------------------------------
# 11. Parametros de consulta -- Contrato Operativo, Seccion 5.2.
#     Valor invalido -> 400 PARAMETRO_INVALIDO. Parametro desconocido: se ignora.
# ---------------------------------------------------------------------------


class ParametroInvalido(Exception):
    pass


def parametro_booleano(nombre, default=False):
    valor = request.args.get(nombre)
    if valor is None:
        return default
    if valor.lower() in ("true", "false"):
        return valor.lower() == "true"
    raise ParametroInvalido(f"{nombre} debe ser true o false")


def parametro_entero(nombre, default, minimo, maximo=None):
    valor = request.args.get(nombre)
    if valor is None:
        return default
    try:
        numero = int(valor)
    except ValueError:
        raise ParametroInvalido(f"{nombre} debe ser un numero entero")
    if numero < minimo or (maximo is not None and numero > maximo):
        rango = f"entre {minimo} y {maximo}" if maximo is not None else f"mayor o igual a {minimo}"
        raise ParametroInvalido(f"{nombre} debe ser {rango}")
    return numero


def parametro_enum(nombre, permitidos, default=None):
    valor = request.args.get(nombre)
    if valor is None:
        return default
    if valor not in permitidos:
        raise ParametroInvalido(f"{nombre} debe ser uno de: {', '.join(permitidos)}")
    return valor


def parametro_multivalor(nombre, permitidos):
    """estado=A&estado=B -> ['A', 'B']. Lista vacia si no viene."""
    valores = request.args.getlist(nombre)
    for valor in valores:
        if valor not in permitidos:
            raise ParametroInvalido(f"{nombre} debe ser uno de: {', '.join(permitidos)}")
    return valores


def paginar(elementos):
    """Devuelve (pagina, total). page >= 1; size entre 1 y SIZE_MAXIMO."""
    page = parametro_entero("page", 1, 1)
    size = parametro_entero("size", SIZE_DEFAULT, 1, SIZE_MAXIMO)
    inicio = (page - 1) * size
    return elementos[inicio:inicio + size], len(elementos)


def respuesta_listado(elementos, total):
    respuesta = jsonify(elementos)
    respuesta.headers["X-Total-Count"] = str(total)
    return respuesta, 200


# ---------------------------------------------------------------------------
# 12. Webhooks -- Contrato Operativo, Seccion 6; Diseno Funcional, 4.13
# ---------------------------------------------------------------------------


def disparar_webhook(orden, estado_anterior, estado_nuevo, operacion):
    """Construye el payload DENTRO de la solicitud original (usa
    g.canal_origen) y lanza la entrega en un hilo separado, sin esperar el
    resultado. El hilo no accede al estado compartido: no necesita candado.
    Devuelve True si habia un webhook registrado."""
    url_destino = webhook_registrado["url"]
    if url_destino is None:
        return False

    canal_origen = g.canal_origen
    payload = {
        "evento": "cambio_estado",
        "orden_id": orden["id"],
        "tipo_orden": orden["tipo_orden"],
        "com_id": orden["com_id"],
        "subscription_id": orden["subscription_id"],
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_nuevo,
        "operacion": operacion,
        "canal_origen": canal_origen,
        "fecha_evento": ahora_iso(),
    }
    hilo = threading.Thread(
        target=_entregar_webhook,
        args=(url_destino, payload, canal_origen),
        daemon=True,
    )
    hilo.start()
    return True


def _entregar_webhook(url_destino, payload, canal_origen):
    """Un solo intento, timeout corto, sin reintentos (Seccion 6.4)."""
    try:
        respuesta = requests.post(
            url_destino,
            json=payload,
            headers={"Content-Type": "application/json", "X-Webhook-Secret": WEBHOOK_SECRET},
            timeout=WEBHOOK_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.RequestException as excepcion:
        _registrar_fallo_webhook(payload, canal_origen, url_destino, str(excepcion))
        return

    if 200 <= respuesta.status_code < 300:
        registrar("WEBHOOK", url_destino, respuesta.status_code, canal_origen=canal_origen)
    else:
        _registrar_fallo_webhook(
            payload, canal_origen, url_destino,
            f"El receptor respondio con codigo {respuesta.status_code}",
        )


def _registrar_fallo_webhook(payload, canal_origen, url_destino, motivo):
    """Conciliacion -- Seccion 6.7."""
    webhooks_fallidos.append({
        "orden_id": payload["orden_id"],
        "operacion": payload["operacion"],
        "canal_origen": canal_origen,
        "url_destino": url_destino,
        "motivo": motivo,
        "fecha_intento": ahora_iso(),
    })
    registrar(
        "WEBHOOK", url_destino, "FALLO",
        error_obj={"codigo": "ENTREGA_WEBHOOK_FALLIDA", "mensaje": motivo},
        canal_origen=canal_origen,
    )


# ---------------------------------------------------------------------------
# 13. Efectos de las ordenes sobre la suscripcion -- Contrato de Datos, 5.3
# ---------------------------------------------------------------------------


def aplicar_transicion(orden, estado_nuevo, marca):
    """Cambia el estado de la orden, agrega la entrada al historial y aplica
    el efecto sobre la suscripcion. Se llama con el candado tomado y solo
    despues de validar todas las reglas."""
    orden["estado"] = estado_nuevo
    orden["fecha_actualizacion"] = marca
    orden["historial"].append({"estado": estado_nuevo, "fecha": marca})

    suscripcion = estado["suscripciones"].get(orden["subscription_id"])
    if suscripcion is None:
        return

    efecto = False
    if estado_nuevo == "COMPLETADA":
        if orden["tipo_orden"] == "ALTA":
            suscripcion["estado"] = "ACTIVA"
            efecto = True
        elif orden["tipo_orden"] == "BAJA":
            suscripcion["estado"] = "BAJA"
            efecto = True
        elif orden["tipo_orden"] == "CAMBIO_OFERTA":
            suscripcion["offer_id"] = orden["offer_id"]
            efecto = True
    elif estado_nuevo == "CANCELADA" and orden["tipo_orden"] == "ALTA":
        suscripcion["estado"] = "ANULADA"
        efecto = True

    if efecto:
        suscripcion["fecha_actualizacion"] = marca


# ---------------------------------------------------------------------------
# 14. Rutas de ordenes
# ---------------------------------------------------------------------------

# --- POST /ordenes -- Diseno Funcional, Seccion 4.4 -------------------------

@app.route(f"{BASE}/ordenes", methods=["POST"])
@requiere_credencial
def crear_orden():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    # RV-01: tipo_orden permitido; ausente = ALTA.
    tipo_orden = datos.get("tipo_orden", "ALTA") if isinstance(datos, dict) else "ALTA"
    if tipo_orden not in TIPOS_ORDEN:
        return responder_error(
            422, "SCHEMA_INVALIDO",
            f"tipo_orden: debe ser uno de {', '.join(TIPOS_ORDEN)}",
        )

    # RV-02 a RV-06: schema del tipo de orden.
    try:
        validate(instance=datos, schema=SCHEMAS_CREACION[tipo_orden])
    except ValidationError as excepcion:
        return error_schema(excepcion)

    if tipo_orden == "RELOCALIZACION":
        if not puntos_finitos(datos["punto_actual"], datos["punto_destino"]):
            return responder_error(422, "SCHEMA_INVALIDO", "punto_actual/punto_destino: x e y deben ser numeros finitos")
        # RN-09: solo depende del contenido, va antes del candado.
        if puntos_iguales(datos["punto_actual"], datos["punto_destino"]):
            return responder_error(422, "PUNTOS_IDENTICOS", "punto_actual y punto_destino no pueden ser iguales")

    com_id = datos["com_id"]
    cliente_id = datos["cliente_id"]

    with candado:
        # RN-01
        if any(orden["com_id"] == com_id for orden in estado["ordenes"].values()):
            return responder_error(409, "COM_ID_DUPLICADO", f"Ya existe una orden con com_id {com_id}")

        suscripcion = None
        if tipo_orden != "ALTA":
            # RN-04
            suscripcion = estado["suscripciones"].get(datos["subscription_id"])
            if suscripcion is None:
                return responder_error(
                    404, "SUSCRIPCION_NO_ENCONTRADA",
                    f"No existe la suscripcion {datos['subscription_id']}",
                )

        oferta = None
        if tipo_orden in ("ALTA", "CAMBIO_OFERTA"):
            # RN-02
            oferta = CATALOGO_POR_ID.get(datos["offer_id"])
            if oferta is None:
                return responder_error(404, "OFERTA_NO_ENCONTRADA", f"No existe la oferta {datos['offer_id']}")

        if suscripcion is not None:
            # RN-05: titularidad antes que cualquier otro dato de la suscripcion.
            if suscripcion["cliente_id"] != cliente_id:
                return responder_error(
                    409, "SUSCRIPCION_NO_PERTENECE_A_CLIENTE",
                    f"La suscripcion {suscripcion['subscription_id']} no pertenece al cliente {cliente_id}",
                )
            # RN-06
            if "tipo_servicio" in datos and datos["tipo_servicio"] != suscripcion["tipo_servicio"]:
                return responder_error(
                    422, "SERVICIO_NO_CORRESPONDE_A_SUSCRIPCION",
                    f"La suscripcion {suscripcion['subscription_id']} es de {suscripcion['tipo_servicio']}, "
                    f"no de {datos['tipo_servicio']}",
                )

        # RN-03: el servicio de la orden es el declarado (ALTA) o el de la suscripcion.
        tipo_servicio = datos["tipo_servicio"] if tipo_orden == "ALTA" else suscripcion["tipo_servicio"]
        if oferta is not None and servicio_de_oferta(oferta["offer_id"]) != tipo_servicio:
            return responder_error(
                422, "OFERTA_NO_CORRESPONDE_A_SERVICIO",
                f"La oferta {oferta['offer_id']} es de {oferta['tipo_servicio']}, no de {tipo_servicio}",
            )

        if suscripcion is not None:
            # RN-07
            if suscripcion["estado"] != "ACTIVA":
                return responder_error(
                    409, "SUSCRIPCION_NO_ACTIVA",
                    f"La suscripcion {suscripcion['subscription_id']} no esta ACTIVA "
                    f"(estado actual: {suscripcion['estado']})",
                )
            # RN-08
            if tipo_orden == "CAMBIO_OFERTA" and oferta["offer_id"] == suscripcion["offer_id"]:
                return responder_error(
                    409, "OFERTA_SIN_CAMBIO",
                    f"La oferta {oferta['offer_id']} ya es la oferta vigente de la suscripcion",
                )

        # Construccion de la orden. RV-09 y RV-10: solo se toman los campos
        # que aplican al tipo; el resto se ignora.
        marca = ahora_iso()
        orden = {
            "id": str(uuid.uuid4()),
            "tipo_orden": tipo_orden,
            "com_id": com_id,
            "cliente_id": cliente_id,
            "tipo_servicio": tipo_servicio,
            "offer_id": datos["offer_id"] if tipo_orden in ("ALTA", "CAMBIO_OFERTA") else None,
            "subscription_id": None if tipo_orden == "ALTA" else suscripcion["subscription_id"],
            "punto_actual": None,
            "punto_destino": None,
            "distancia_m": None,
            "duracion_estimada_ms": None,
            "prioridad": datos.get("prioridad", "MEDIA"),
            "descripcion": datos.get("descripcion", ""),
            "estado": "RECIBIDA",
            "fecha_creacion": marca,
            "fecha_actualizacion": marca,
            "historial": [{"estado": "RECIBIDA", "fecha": marca}],
        }

        if tipo_orden == "RELOCALIZACION":
            orden["punto_actual"] = datos["punto_actual"]
            orden["punto_destino"] = datos["punto_destino"]
            distancia, duracion, _ = calcular_relocalizacion(datos["punto_actual"], datos["punto_destino"])
            orden["distancia_m"] = distancia
            orden["duracion_estimada_ms"] = duracion

        if tipo_orden == "ALTA":
            # Contrato de Datos, Seccion 4.3: correlativo por servicio, nunca reutilizado.
            estado["correlativos"][tipo_servicio] += 1
            subscription_id = f"{PREFIJO_SERVICIO[tipo_servicio]}{estado['correlativos'][tipo_servicio]:06d}"
            orden["subscription_id"] = subscription_id
            estado["suscripciones"][subscription_id] = {
                "subscription_id": subscription_id,
                "cliente_id": cliente_id,
                "tipo_servicio": tipo_servicio,
                "offer_id": orden["offer_id"],
                "estado": "PENDIENTE",
                "orden_alta_id": orden["id"],
                "fecha_creacion": marca,
                "fecha_actualizacion": marca,
            }

        estado["ordenes"][orden["id"]] = orden
        try:
            guardar_estado()
        except OSError:
            return error_persistencia()
        respuesta = orden_publica(orden)

    registrar(request.method, request.path, 201)
    return jsonify(respuesta), 201


# --- GET /ordenes -- Diseno Funcional, Seccion 4.5 --------------------------

CAMPOS_ORDENAMIENTO = [
    "fecha_creacion", "com_id", "cliente_id", "subscription_id",
    "tipo_orden", "tipo_servicio", "estado", "prioridad",
]


@app.route(f"{BASE}/ordenes", methods=["GET"])
@requiere_credencial
def listar_ordenes():
    try:
        filtros = {
            "cliente_id": request.args.get("cliente_id"),
            "subscription_id": request.args.get("subscription_id"),
            "com_id": request.args.get("com_id"),
            "tipo_servicio": parametro_enum("tipo_servicio", TIPOS_SERVICIO),
            "tipo_orden": parametro_enum("tipo_orden", TIPOS_ORDEN),
        }
        estados = parametro_multivalor("estado", ESTADOS_ORDEN)
        sort_by = parametro_enum("sortBy", CAMPOS_ORDENAMIENTO, "fecha_creacion")
        orden_desc = parametro_enum("order", ["asc", "desc"], "asc") == "desc"
        incluir_oferta = parametro_booleano("includeOferta")
        parametro_entero("page", 1, 1)
        parametro_entero("size", SIZE_DEFAULT, 1, SIZE_MAXIMO)
    except ParametroInvalido as excepcion:
        return responder_error(400, "PARAMETRO_INVALIDO", str(excepcion))

    with candado:
        # Copia bajo candado, en orden de creacion (orden de insercion).
        ordenes = [orden_publica(orden, incluir_oferta) for orden in estado["ordenes"].values()]

    for campo, valor in filtros.items():
        if valor is not None:
            ordenes = [orden for orden in ordenes if orden[campo] == valor]
    if estados:
        ordenes = [orden for orden in ordenes if orden["estado"] in estados]

    # sorted es estable: los empates quedan en orden de creacion, tambien en desc.
    ordenes = sorted(ordenes, key=lambda orden: orden[sort_by], reverse=orden_desc)
    pagina, total = paginar(ordenes)
    registrar(request.method, request.path, 200)
    return respuesta_listado(pagina, total)


# --- GET /ordenes/<id> -- Diseno Funcional, Seccion 4.6 ---------------------

@app.route(f"{BASE}/ordenes/<id_orden>", methods=["GET"])
@requiere_credencial
def obtener_orden(id_orden):
    with candado:
        orden = estado["ordenes"].get(id_orden)
        representacion = None
        if orden is not None:
            try:
                incluir_oferta = parametro_booleano("includeOferta")
            except ParametroInvalido as excepcion:
                return responder_error(400, "PARAMETRO_INVALIDO", str(excepcion))
            representacion = orden_publica(orden, incluir_oferta)

    if representacion is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")
    registrar(request.method, request.path, 200)
    return jsonify(representacion), 200


# --- PUT /ordenes/<id> -- Diseno Funcional, Seccion 4.7 ---------------------

@app.route(f"{BASE}/ordenes/<id_orden>", methods=["PUT"])
@requiere_credencial
def reemplazar_orden(id_orden):
    if id_orden not in estado["ordenes"]:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    # RV-07 (y RV-05 para prioridad)
    try:
        validate(instance=datos, schema=REEMPLAZO_SCHEMA)
    except ValidationError as excepcion:
        return error_schema(excepcion)

    with candado:
        orden = estado["ordenes"][id_orden]
        # RN-12
        if orden["estado"] in ESTADOS_TERMINALES:
            return responder_error(
                409, "ORDEN_EN_ESTADO_TERMINAL",
                f"No se puede modificar una orden en estado {orden['estado']}",
            )
        # RN-13: los inmutables que vengan deben coincidir. RV-09: solo lectura se ignora.
        for campo in CAMPOS_INMUTABLES:
            if campo in datos and datos[campo] != orden[campo]:
                return responder_error(
                    409, "CAMPO_INMUTABLE",
                    f"{campo} no se puede modificar (valor vigente: {orden[campo]})",
                )

        orden["prioridad"] = datos["prioridad"]
        orden["descripcion"] = datos["descripcion"]
        orden["fecha_actualizacion"] = ahora_iso()
        try:
            guardar_estado()
        except OSError:
            return error_persistencia()
        respuesta = orden_publica(orden)

    # PUT nunca modifica estado: no dispara webhook (Contrato Operativo, 6.3).
    registrar(request.method, request.path, 200)
    return jsonify(respuesta), 200


# --- PATCH /ordenes/<id> -- Diseno Funcional, Seccion 4.8 -------------------

@app.route(f"{BASE}/ordenes/<id_orden>", methods=["PATCH"])
@requiere_credencial
def actualizar_orden(id_orden):
    if id_orden not in estado["ordenes"]:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    # RV-08 (y RV-05 para estado)
    try:
        validate(instance=datos, schema=ACTUALIZACION_SCHEMA)
    except ValidationError as excepcion:
        return error_schema(excepcion)

    with candado:
        orden = estado["ordenes"][id_orden]
        estado_anterior = orden["estado"]
        estado_nuevo = datos.get("estado")

        # RN-12
        if estado_anterior in ESTADOS_TERMINALES:
            return responder_error(
                409, "ORDEN_EN_ESTADO_TERMINAL",
                f"No se puede modificar una orden en estado {estado_anterior}",
            )

        if estado_nuevo is not None:
            # RN-11
            if estado_nuevo not in TRANSICIONES_VALIDAS[estado_anterior]:
                return responder_error(
                    409, "TRANSICION_INVALIDA",
                    f"No se puede pasar de {estado_anterior} a {estado_nuevo}",
                )
            if estado_nuevo == "EN_PROGRESO":
                suscripcion = estado["suscripciones"][orden["subscription_id"]]
                if orden["tipo_orden"] != "ALTA":
                    # RN-07, reevaluada: la suscripcion pudo cambiar mientras la orden esperaba.
                    if suscripcion["estado"] != "ACTIVA":
                        return responder_error(
                            409, "SUSCRIPCION_NO_ACTIVA",
                            f"La suscripcion {suscripcion['subscription_id']} no esta ACTIVA "
                            f"(estado actual: {suscripcion['estado']})",
                        )
                    # RN-08, reevaluada.
                    if orden["tipo_orden"] == "CAMBIO_OFERTA" and orden["offer_id"] == suscripcion["offer_id"]:
                        return responder_error(
                            409, "OFERTA_SIN_CAMBIO",
                            f"La oferta {orden['offer_id']} ya es la oferta vigente de la suscripcion",
                        )
                # RN-10: una sola orden EN_PROGRESO por suscripcion.
                for otra in estado["ordenes"].values():
                    if (
                        otra["id"] != orden["id"]
                        and otra["subscription_id"] == orden["subscription_id"]
                        and otra["estado"] == "EN_PROGRESO"
                    ):
                        return responder_error(
                            409, "ORDEN_EN_CURSO",
                            f"La orden {otra['id']} (com_id {otra['com_id']}) de la suscripcion "
                            f"{orden['subscription_id']} ya esta EN_PROGRESO",
                        )

        # Todas las validaciones pasaron: recien ahora se modifica la orden.
        marca = ahora_iso()
        if "descripcion" in datos:
            orden["descripcion"] = datos["descripcion"]
            orden["fecha_actualizacion"] = marca
        if estado_nuevo is not None:
            aplicar_transicion(orden, estado_nuevo, marca)
        try:
            guardar_estado()
        except OSError:
            return error_persistencia()
        respuesta = orden_publica(orden)

    # Solo un cambio de estado dispara webhook (Contrato Operativo, 6.3).
    if estado_nuevo is not None and disparar_webhook(orden, estado_anterior, estado_nuevo, "PATCH"):
        respuesta["notificacion_webhook"] = "pendiente"

    registrar(request.method, request.path, 200)
    return jsonify(respuesta), 200


# --- DELETE /ordenes/<id> -- Diseno Funcional, Seccion 4.9 ------------------

@app.route(f"{BASE}/ordenes/<id_orden>", methods=["DELETE"])
@requiere_credencial
def cancelar_orden(id_orden):
    if id_orden not in estado["ordenes"]:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")

    with candado:
        orden = estado["ordenes"][id_orden]
        estado_anterior = orden["estado"]
        # RN-12
        if estado_anterior in ESTADOS_TERMINALES:
            return responder_error(
                409, "ORDEN_EN_ESTADO_TERMINAL",
                f"No se puede cancelar una orden en estado {estado_anterior}",
            )
        aplicar_transicion(orden, "CANCELADA", ahora_iso())
        try:
            guardar_estado()
        except OSError:
            return error_persistencia()
        respuesta = orden_publica(orden)

    if disparar_webhook(orden, estado_anterior, "CANCELADA", "DELETE"):
        respuesta["notificacion_webhook"] = "pendiente"

    registrar(request.method, request.path, 200)
    return jsonify(respuesta), 200


# --- GET /ordenes/<id>/trazabilidad -- Diseno Funcional, Seccion 4.10 -------

@app.route(f"{BASE}/ordenes/<id_orden>/trazabilidad", methods=["GET"])
@requiere_credencial
def obtener_trazabilidad(id_orden):
    with candado:
        orden = estado["ordenes"].get(id_orden)
        copia = json.loads(json.dumps(orden)) if orden is not None else None

    if copia is None:
        return responder_error(404, "ORDEN_NO_ENCONTRADA", f"No existe una orden con id {id_orden}")
    try:
        idioma = parametro_enum("idioma", IDIOMAS, "en")
    except ParametroInvalido as excepcion:
        return responder_error(400, "PARAMETRO_INVALIDO", str(excepcion))

    trabajo = None
    if copia["tipo_orden"] == "RELOCALIZACION":
        distancia, duracion, pasos = calcular_relocalizacion(copia["punto_actual"], copia["punto_destino"], idioma)
        trabajo = {"distancia_m": distancia, "duracion_estimada_ms": duracion, "pasos": pasos}

    registrar(request.method, request.path, 200)
    return jsonify({
        "orden_id": copia["id"],
        "com_id": copia["com_id"],
        "tipo_orden": copia["tipo_orden"],
        "subscription_id": copia["subscription_id"],
        "idioma": idioma,
        "historial": copia["historial"],
        "trabajo": trabajo,
    }), 200


# ---------------------------------------------------------------------------
# 15. Suscripciones y ofertas -- Diseno Funcional, Secciones 4.11 y 4.12
# ---------------------------------------------------------------------------

@app.route(f"{BASE}/suscripciones", methods=["GET"])
@requiere_credencial
def listar_suscripciones():
    try:
        cliente_id = request.args.get("cliente_id")
        tipo_servicio = parametro_enum("tipo_servicio", TIPOS_SERVICIO)
        estados = parametro_multivalor("estado", ESTADOS_SUSCRIPCION)
        parametro_entero("page", 1, 1)
        parametro_entero("size", SIZE_DEFAULT, 1, SIZE_MAXIMO)
    except ParametroInvalido as excepcion:
        return responder_error(400, "PARAMETRO_INVALIDO", str(excepcion))

    with candado:
        suscripciones = [suscripcion_publica(s) for s in estado["suscripciones"].values()]

    if cliente_id is not None:
        suscripciones = [s for s in suscripciones if s["cliente_id"] == cliente_id]
    if tipo_servicio is not None:
        suscripciones = [s for s in suscripciones if s["tipo_servicio"] == tipo_servicio]
    if estados:
        suscripciones = [s for s in suscripciones if s["estado"] in estados]

    suscripciones.sort(key=lambda s: s["subscription_id"])
    pagina, total = paginar(suscripciones)
    registrar(request.method, request.path, 200)
    return respuesta_listado(pagina, total)


@app.route(f"{BASE}/suscripciones/<subscription_id>", methods=["GET"])
@requiere_credencial
def obtener_suscripcion(subscription_id):
    with candado:
        suscripcion = estado["suscripciones"].get(subscription_id)
        representacion = suscripcion_publica(suscripcion) if suscripcion else None

    if representacion is None:
        return responder_error(404, "SUSCRIPCION_NO_ENCONTRADA", f"No existe la suscripcion {subscription_id}")
    registrar(request.method, request.path, 200)
    return jsonify(representacion), 200


@app.route(f"{BASE}/ofertas", methods=["GET"])
@requiere_credencial
def listar_ofertas():
    try:
        texto = request.args.get("q")
        tipo_servicio = parametro_enum("tipo_servicio", TIPOS_SERVICIO)
        limite = parametro_entero("limit", None, 1)
    except ParametroInvalido as excepcion:
        return responder_error(400, "PARAMETRO_INVALIDO", str(excepcion))

    # El catalogo es constante: no se toma el candado.
    ofertas = list(CATALOGO)
    if texto:
        ofertas = [o for o in ofertas if texto.casefold() in o["nombre"].casefold()]
    if tipo_servicio is not None:
        ofertas = [o for o in ofertas if o["tipo_servicio"] == tipo_servicio]
    if limite is not None:
        ofertas = ofertas[:limite]

    registrar(request.method, request.path, 200)
    return jsonify(ofertas), 200


@app.route(f"{BASE}/ofertas/<offer_id>", methods=["GET"])
@requiere_credencial
def obtener_oferta(offer_id):
    oferta = CATALOGO_POR_ID.get(offer_id)
    if oferta is None:
        return responder_error(404, "OFERTA_NO_ENCONTRADA", f"No existe la oferta {offer_id}")
    registrar(request.method, request.path, 200)
    return jsonify(oferta), 200


# ---------------------------------------------------------------------------
# 16. Webhooks -- Contrato Operativo, Secciones 6.2 y 6.7
# ---------------------------------------------------------------------------

@app.route(f"{BASE}/webhooks", methods=["POST"])
@requiere_credencial
def registrar_webhook():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error
    try:
        validate(instance=datos, schema=WEBHOOK_SCHEMA)
    except ValidationError as excepcion:
        return error_schema(excepcion)

    webhook_registrado["url"] = datos["url"]
    registrar(request.method, request.path, 201)
    return jsonify({"url": webhook_registrado["url"]}), 201


@app.route(f"{BASE}/webhooks/fallos", methods=["GET"])
@requiere_credencial
def listar_webhooks_fallidos():
    registrar(request.method, request.path, 200)
    return jsonify(list(webhooks_fallidos)), 200


# ---------------------------------------------------------------------------
# 17. Documentacion navegable -- Contrato Operativo, Seccion 5.4
#
#     Especificacion OpenAPI escrita a mano (Diseno Funcional, Seccion 5).
#     Los schemas de solicitud reutilizan los mismos diccionarios jsonschema
#     con que se valida: una sola fuente para el contrato y la validacion.
# ---------------------------------------------------------------------------

def _ref(nombre):
    return {"$ref": f"#/components/schemas/{nombre}"}


def _error_resp(descripcion):
    return {"description": descripcion, "content": {"application/json": {"schema": _ref("Error")}}}


def _json_resp(descripcion, schema):
    return {"description": descripcion, "content": {"application/json": {"schema": schema}}}


def _param(nombre, ubicacion, schema, descripcion, requerido=False, explode=None):
    parametro = {"name": nombre, "in": ubicacion, "required": requerido, "schema": schema, "description": descripcion}
    if explode is not None:
        parametro["explode"] = explode
    return parametro


def _solo_lectura(schema, descripcion=None):
    """Copia de un schema para las respuestas, marcada como generada por SOM."""
    copia = {**schema, "readOnly": True}
    if descripcion is not None:
        copia["description"] = descripcion
    return copia


UUID_SCHEMA = {"type": "string", "format": "uuid"}
FECHA_SCHEMA = {"type": "string", "format": "date-time", "readOnly": True}
COM_ID_SCHEMA = PROPIEDADES_COMUNES["com_id"]
COM_ID_FILTRO = {"type": "string", "pattern": "^[0-9]{7}$"}
SUBSCRIPTION_ID_FILTRO = {"type": "string", "pattern": "^[0-9]{8}$"}
OFFER_ID_FILTRO = {"type": "string", "pattern": "^[0-9]{6}$"}

ID_ORDEN_PARAM = _param("id", "path", UUID_SCHEMA,
                        "id (UUID) de la orden, el que entrega SOM al crearla. No es el com_id.", True)
PAGINACION_PARAMS = [
    _param("page", "query", {"type": "integer", "minimum": 1, "default": 1}, "Página solicitada, desde 1"),
    _param("size", "query", {"type": "integer", "minimum": 1, "maximum": SIZE_MAXIMO, "default": SIZE_DEFAULT},
           f"Elementos por página, de 1 a {SIZE_MAXIMO}"),
]
TOTAL_HEADER = {"X-Total-Count": {"description": "Total de elementos que cumplen los filtros, en todas las "
                                                   "páginas", "schema": {"type": "integer"}}}

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "SOM API Demo -- Orden de Servicio",
        "version": "2.1",
        "description": (
            "API demo de Service Order Management, CUY6142 Duoc UC.\n\n"
            "**Para autorizar:** (1) en Authorize, sección BasicAuth, ingrese usuario gui y contraseña "
            "Cuy6142!; (2) ejecute POST /loginViaBasic y copie el token, sin comillas; (3) en Authorize, "
            "sección ApiKeyHeader, pegue el token.\n\n"
            "**Use esta página para consultar.** Lo que se crea o modifica con Try it out queda guardado en "
            "SOM, igual que desde Postman.\n\n"
            "**Formatos:** Swagger revisa el formato de los parámetros de la ruta y de los filtros antes de "
            "enviar la solicitud. La API no los revisa: desde Postman o Python, un valor con otro formato "
            "responde 404 (ruta) o una lista vacía (filtro)."
        ),
    },
    "servers": [{"url": BASE}],
    "security": [{"ApiKeyHeader": []}, {"ApiKeyQuery": []}],
    "components": {
        "securitySchemes": {
            "ApiKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-KEY"},
            "ApiKeyQuery": {"type": "apiKey", "in": "query", "name": "key"},
            "BasicAuth": {"type": "http", "scheme": "basic"},
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {"error": {"type": "object", "properties": {
                    "codigo": {"type": "string"}, "mensaje": {"type": "string"}}}},
            },
            "Token": {"type": "object", "properties": {"token": {
                "type": "string", "pattern": "^[a-z]+\\|[A-Za-z0-9_-]{43}$",
                "description": "Token de sesión: usuario, el carácter | y 43 caracteres al azar "
                               "(ej. gui|yOg3m_...). Se envía en el header X-API-KEY o en el parámetro key. "
                               "Se pierde si SOM se reinicia."}}},
            "Punto": PUNTO_SCHEMA,
            "Oferta": {"type": "object", "description": "Oferta del catálogo. Solo lectura: el catálogo es fijo.",
                       "properties": {
                           "offer_id": OFFER_ID_SCHEMA,
                           "nombre": {"type": "string", "description": "Nombre comercial de la oferta."},
                           "tipo_servicio": {"type": "string", "enum": TIPOS_SERVICIO,
                                             "description": "Servicio de la oferta. Coincide con el prefijo "
                                                            "de offer_id."}}},
            "Orden": {"type": "object", "description": "Orden de servicio. Todos los campos están siempre "
                      "presentes; un campo que no aplica al tipo de orden vale null.", "properties": {
                "id": _solo_lectura(UUID_SCHEMA, "Identificador técnico que asigna SOM (UUID). Se usa en la "
                                                 "ruta /ordenes/{id}."),
                "tipo_orden": PROPIEDADES_COMUNES["tipo_orden"],
                "com_id": COM_ID_SCHEMA,
                "cliente_id": PROPIEDADES_COMUNES["cliente_id"],
                "tipo_servicio": {"type": "string", "enum": TIPOS_SERVICIO,
                                  "description": "Servicio. En BAJA, CAMBIO_OFERTA y RELOCALIZACION lo toma SOM "
                                                 "de la suscripción."},
                "offer_id": {**OFFER_ID_SCHEMA, "nullable": True,
                             "description": "Oferta contratada (ALTA) u oferta nueva (CAMBIO_OFERTA), 6 dígitos. "
                                            "null en BAJA y RELOCALIZACION."},
                "subscription_id": SUBSCRIPTION_ID_SCHEMA,
                "punto_actual": {"allOf": [_ref("Punto")], "nullable": True,
                                 "description": "Ubicación actual del punto de red. null si no es RELOCALIZACION."},
                "punto_destino": {"allOf": [_ref("Punto")], "nullable": True,
                                  "description": "Ubicación de destino. null si no es RELOCALIZACION."},
                "distancia_m": {"type": "number", "nullable": True, "readOnly": True,
                                "description": "Metros de cable a tender, sumando los tramos este-oeste y "
                                               "norte-sur, con 3 decimales. Lo calcula SOM. null si no es "
                                               "RELOCALIZACION."},
                "duracion_estimada_ms": {"type": "integer", "nullable": True, "readOnly": True,
                                         "description": "Duración estimada del trabajo, en milisegundos. La "
                                                        "calcula SOM. null si no es RELOCALIZACION."},
                "prioridad": PROPIEDADES_COMUNES["prioridad"],
                "descripcion": PROPIEDADES_COMUNES["descripcion"],
                "estado": {"type": "string", "enum": ESTADOS_ORDEN, "readOnly": True,
                           "description": "Estado actual. Toda orden nace RECIBIDA; cambia con PATCH "
                                          "(transición de estado) o DELETE (cancelación)."},
                "fecha_creacion": {**FECHA_SCHEMA, "description": "Fecha y hora de creación, en UTC."},
                "fecha_actualizacion": {**FECHA_SCHEMA, "description": "Fecha y hora del último cambio, en UTC."},
                "oferta": {"allOf": [_ref("Oferta")], "nullable": True, "readOnly": True,
                           "description": "Datos completos de la oferta. Solo aparece con includeOferta=true."},
            }},
            "Suscripcion": {"type": "object", "description": "Servicio contratado por un cliente. Solo lectura: "
                            "se crea y cambia como efecto de las ordenes.", "properties": {
                "subscription_id": SUBSCRIPTION_ID_SCHEMA,
                "cliente_id": {"type": "string", "description": "Titular: el cliente_id del ALTA que la creó."},
                "tipo_servicio": {"type": "string", "enum": TIPOS_SERVICIO,
                                  "description": "Servicio. Coincide con el prefijo de subscription_id."},
                "offer_id": {**OFFER_ID_SCHEMA, "description": "Oferta vigente, 6 dígitos. Cambia al "
                                                               "completarse un CAMBIO_OFERTA."},
                "estado": {"type": "string", "enum": ESTADOS_SUSCRIPCION,
                           "description": "PENDIENTE al crear el ALTA; ACTIVA al completarlo; ANULADA si el ALTA "
                                          "se cancela; BAJA al completarse una BAJA. Solo una suscripción ACTIVA "
                                          "admite BAJA, CAMBIO_OFERTA y RELOCALIZACION."},
                "orden_alta_id": {**UUID_SCHEMA, "description": "id de la orden de ALTA que creó la suscripción."},
                "fecha_creacion": {**FECHA_SCHEMA, "description": "Fecha y hora de creación, en UTC."},
                "fecha_actualizacion": {**FECHA_SCHEMA, "description": "Fecha y hora del último cambio, en UTC."}}},
            "Trazabilidad": {"type": "object", "description": "Historial de estados de una orden y, en una "
                             "RELOCALIZACION, el detalle del trabajo.", "properties": {
                "orden_id": {**UUID_SCHEMA, "description": "id de la orden."},
                "com_id": COM_ID_SCHEMA,
                "tipo_orden": {"type": "string", "enum": TIPOS_ORDEN, "description": "Tipo de la orden."},
                "subscription_id": SUBSCRIPTION_ID_SCHEMA,
                "idioma": {"type": "string", "enum": IDIOMAS, "default": "en",
                           "description": "Idioma de los textos de trabajo.pasos."},
                "historial": {"type": "array", "description": "Un elemento por cada estado que tuvo la orden, "
                              "desde RECIBIDA, en orden cronológico.", "items": {"type": "object", "properties": {
                    "estado": {"type": "string", "enum": ESTADOS_ORDEN, "description": "Estado alcanzado."},
                    "fecha": {"type": "string", "format": "date-time",
                              "description": "Fecha y hora en que la orden alcanzó ese estado, en UTC."}}}},
                "trabajo": {"type": "object", "nullable": True,
                            "description": "Detalle del trabajo de una RELOCALIZACION. null en los demás tipos.",
                            "properties": {
                    "distancia_m": {"type": "number", "description": "Metros de cable, igual que en la orden."},
                    "duracion_estimada_ms": {"type": "integer",
                                             "description": "Duración total en milisegundos, igual que en la orden."},
                    "pasos": {"type": "array", "description": "Pasos en orden de ejecución.",
                              "items": {"type": "object", "properties": {
                        "secuencia": {"type": "integer", "description": "Número de paso, desde 1."},
                        "texto": {"type": "string", "description": "Instrucción del paso, en el idioma pedido."},
                        "distancia_m": {"type": "number", "description": "Metros de cable del paso; 0 si no "
                                                                         "hay tendido."},
                        "duracion_ms": {"type": "integer", "description": "Duración del paso, en milisegundos."}}}}}},
            }},
            "CreacionAlta": SCHEMAS_CREACION["ALTA"],
            "CreacionBaja": SCHEMAS_CREACION["BAJA"],
            "CreacionCambioOferta": SCHEMAS_CREACION["CAMBIO_OFERTA"],
            "CreacionRelocalizacion": SCHEMAS_CREACION["RELOCALIZACION"],
            "Reemplazo": REEMPLAZO_SCHEMA,
            "ActualizacionParcial": ACTUALIZACION_SCHEMA,
            "Webhook": WEBHOOK_SCHEMA,
        },
    },
    "paths": {
        "/loginViaBasic": {"post": {
            "tags": ["Autenticación"], "summary": "Obtener un token de sesión",
            "security": [{"BasicAuth": []}],
            "responses": {"200": _json_resp("Token emitido", _ref("Token")),
                          "401": _error_resp("CREDENCIALES_INVALIDAS")}}},
        "/ordenes": {
            "post": {
                "tags": ["Órdenes"], "summary": "Crear orden (ALTA, BAJA, CAMBIO_OFERTA, RELOCALIZACION)",
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": {"oneOf": [_ref("CreacionAlta"), _ref("CreacionBaja"),
                                         _ref("CreacionCambioOferta"), _ref("CreacionRelocalizacion")]},
                    "examples": {
                        "ALTA": {"value": {"tipo_orden": "ALTA", "com_id": "1000001", "cliente_id": "CL-10457",
                                           "tipo_servicio": "INTERNET", "offer_id": "200102"}},
                        "RELOCALIZACION": {"value": {
                            "tipo_orden": "RELOCALIZACION", "com_id": "1000002", "cliente_id": "CL-10457",
                            "subscription_id": "20000001",
                            "punto_actual": {"x": 2.5, "y": 1.75, "referencia": "Living"},
                            "punto_destino": {"x": 6.125, "y": 4.5, "referencia": "Dormitorio 2"}}},
                        "CAMBIO_OFERTA": {"value": {"tipo_orden": "CAMBIO_OFERTA", "com_id": "1000003",
                                                    "cliente_id": "CL-10457", "subscription_id": "20000001",
                                                    "offer_id": "200103"}},
                        "BAJA": {"value": {"tipo_orden": "BAJA", "com_id": "1000004", "cliente_id": "CL-10457",
                                           "subscription_id": "20000001"}},
                    }}}},
                "responses": {"201": _json_resp("Orden creada", _ref("Orden")),
                              "400": _error_resp("JSON_INVALIDO"), "401": _error_resp("NO_AUTORIZADO"),
                              "404": _error_resp("SUSCRIPCION_NO_ENCONTRADA u OFERTA_NO_ENCONTRADA"),
                              "409": _error_resp("Regla de negocio sobre datos almacenados"),
                              "422": _error_resp("SCHEMA_INVALIDO u otra regla de contenido")}},
            "get": {
                "tags": ["Órdenes"], "summary": "Listar órdenes",
                "parameters": [
                    _param("cliente_id", "query", {"type": "string"}, "Filtro por igualdad"),
                    _param("subscription_id", "query", SUBSCRIPTION_ID_FILTRO,
                           "Filtro por igualdad. 8 dígitos"),
                    _param("com_id", "query", COM_ID_FILTRO, "Filtro por igualdad. 7 dígitos"),
                    _param("tipo_servicio", "query", {"type": "string", "enum": TIPOS_SERVICIO}, "Filtro por servicio"),
                    _param("tipo_orden", "query", {"type": "string", "enum": TIPOS_ORDEN}, "Filtro por tipo de orden"),
                    _param("estado", "query", {"type": "array", "items": {"type": "string", "enum": ESTADOS_ORDEN}},
                           "Uno o mas estados (se repite el parametro)", explode=True),
                    _param("sortBy", "query", {"type": "string", "enum": CAMPOS_ORDENAMIENTO,
                                               "default": "fecha_creacion"}, "Campo de ordenamiento"),
                    _param("order", "query", {"type": "string", "enum": ["asc", "desc"], "default": "asc"},
                           "Sentido del ordenamiento"),
                    *PAGINACION_PARAMS,
                    _param("includeOferta", "query", {"type": "boolean", "default": False},
                           "Agrega el campo oferta a cada orden"),
                ],
                "responses": {"200": {**_json_resp("Página de órdenes", {"type": "array", "items": _ref("Orden")}),
                                      "headers": TOTAL_HEADER},
                              "400": _error_resp("PARAMETRO_INVALIDO"), "401": _error_resp("NO_AUTORIZADO")}},
        },
        "/ordenes/{id}": {
            "get": {
                "tags": ["Órdenes"], "summary": "Consultar una orden",
                "parameters": [ID_ORDEN_PARAM, _param("includeOferta", "query", {"type": "boolean", "default": False},
                                                       "Agrega el campo oferta")],
                "responses": {"200": _json_resp("Orden", _ref("Orden")), "401": _error_resp("NO_AUTORIZADO"),
                              "404": _error_resp("ORDEN_NO_ENCONTRADA")}},
            "put": {
                "tags": ["Órdenes"], "summary": "Reemplazo completo de los campos editables",
                "parameters": [ID_ORDEN_PARAM],
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": _ref("Reemplazo"),
                    "example": {"prioridad": "ALTA", "descripcion": "Cliente solicita visita en horario AM"}}}},
                "responses": {"200": _json_resp("Orden", _ref("Orden")), "404": _error_resp("ORDEN_NO_ENCONTRADA"),
                              "409": _error_resp("ORDEN_EN_ESTADO_TERMINAL o CAMPO_INMUTABLE"),
                              "422": _error_resp("SCHEMA_INVALIDO")}},
            "patch": {
                "tags": ["Órdenes"], "summary": "Actualizar descripción y/o transicionar estado",
                "parameters": [ID_ORDEN_PARAM],
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": _ref("ActualizacionParcial"), "example": {"estado": "EN_PROGRESO"}}}},
                "responses": {"200": _json_resp("Orden", _ref("Orden")), "404": _error_resp("ORDEN_NO_ENCONTRADA"),
                              "409": _error_resp("Regla de negocio sobre datos almacenados"),
                              "422": _error_resp("SCHEMA_INVALIDO")}},
            "delete": {
                "tags": ["Órdenes"], "summary": "Cancelar orden",
                "parameters": [ID_ORDEN_PARAM],
                "responses": {"200": _json_resp("Orden cancelada", _ref("Orden")),
                              "404": _error_resp("ORDEN_NO_ENCONTRADA"),
                              "409": _error_resp("ORDEN_EN_ESTADO_TERMINAL")}},
        },
        "/ordenes/{id}/trazabilidad": {"get": {
            "tags": ["Órdenes"], "summary": "Consultar la trazabilidad de una orden",
            "parameters": [ID_ORDEN_PARAM, _param("idioma", "query", {"type": "string", "enum": IDIOMAS,
                                                                       "default": "en"}, "Idioma de los pasos")],
            "responses": {"200": _json_resp("Trazabilidad", _ref("Trazabilidad")),
                          "400": _error_resp("PARAMETRO_INVALIDO"), "404": _error_resp("ORDEN_NO_ENCONTRADA")}}},
        "/suscripciones": {"get": {
            "tags": ["Suscripciones"], "summary": "Listar suscripciones",
            "parameters": [
                _param("cliente_id", "query", {"type": "string"}, "Filtro por igualdad"),
                _param("tipo_servicio", "query", {"type": "string", "enum": TIPOS_SERVICIO}, "Filtro por servicio"),
                _param("estado", "query", {"type": "array", "items": {"type": "string", "enum": ESTADOS_SUSCRIPCION}},
                       "Uno o mas estados (se repite el parametro)", explode=True),
                *PAGINACION_PARAMS,
            ],
            "responses": {"200": {**_json_resp("Página de suscripciones",
                                               {"type": "array", "items": _ref("Suscripcion")}),
                                  "headers": TOTAL_HEADER},
                          "400": _error_resp("PARAMETRO_INVALIDO")}}},
        "/suscripciones/{subscription_id}": {"get": {
            "tags": ["Suscripciones"], "summary": "Consultar una suscripción",
            "parameters": [_param("subscription_id", "path", SUBSCRIPTION_ID_FILTRO,
                                  "subscription_id de la suscripción, 8 dígitos", True)],
            "responses": {"200": _json_resp("Suscripción", _ref("Suscripcion")),
                          "404": _error_resp("SUSCRIPCION_NO_ENCONTRADA")}}},
        "/ofertas": {"get": {
            "tags": ["Ofertas"], "summary": "Listar o buscar ofertas",
            "parameters": [
                _param("q", "query", {"type": "string"}, "Texto contenido en el nombre"),
                _param("tipo_servicio", "query", {"type": "string", "enum": TIPOS_SERVICIO}, "Filtro por servicio"),
                _param("limit", "query", {"type": "integer", "minimum": 1}, "Cantidad máxima de ofertas"),
            ],
            "responses": {"200": _json_resp("Ofertas", {"type": "array", "items": _ref("Oferta")}),
                          "400": _error_resp("PARAMETRO_INVALIDO")}}},
        "/ofertas/{offer_id}": {"get": {
            "tags": ["Ofertas"], "summary": "Consultar una oferta",
            "parameters": [_param("offer_id", "path", OFFER_ID_FILTRO, "offer_id de la oferta, 6 dígitos", True)],
            "responses": {"200": _json_resp("Oferta", _ref("Oferta")),
                          "404": _error_resp("OFERTA_NO_ENCONTRADA")}}},
        "/webhooks": {"post": {
            "tags": ["Webhooks"], "summary": "Registrar receptor de notificaciones",
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": _ref("Webhook"), "example": {"url": "http://crm-som:8082/webhooks/ordenes"}}}},
            "responses": {"201": {"description": "Registrado"}, "422": _error_resp("SCHEMA_INVALIDO")}}},
        "/webhooks/fallos": {"get": {
            "tags": ["Webhooks"], "summary": "Consultar entregas fallidas",
            "responses": {"200": {"description": "Lista de intentos fallidos"}}}},
    },
}

# Toda ruta que exige credencial documenta el 401 -- Contrato Operativo, Seccion 4.
for _ruta, _operaciones in OPENAPI["paths"].items():
    if _ruta != "/loginViaBasic":
        for _operacion in _operaciones.values():
            _operacion["responses"].setdefault("401", _error_resp("NO_AUTORIZADO"))

SWAGGER_UI_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>SOM API Demo v2 -- Documentacion</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({ url: "%s/openapi.json", dom_id: "#swagger-ui" });
  </script>
</body>
</html>
""" % BASE


@app.route(f"{BASE}/openapi.json", methods=["GET"])
def especificacion_openapi():
    return jsonify(OPENAPI), 200


@app.route(f"{BASE}/docs", methods=["GET"])
def documentacion():
    return Response(SWAGGER_UI_HTML, mimetype="text/html")


# ---------------------------------------------------------------------------
# 18. Manejador generico de errores no controlados -- Contrato Operativo,
#     Seccion 8.1. Deja pasar los errores propios de Flask/Werkzeug (404 por
#     ruta inexistente, 405 por metodo no soportado).
# ---------------------------------------------------------------------------

@app.errorhandler(Exception)
def manejar_error_no_controlado(excepcion):
    if isinstance(excepcion, HTTPException):
        return excepcion
    return responder_error(500, "ERROR_INTERNO", "Fallo no controlado del servidor")


# ---------------------------------------------------------------------------
# 19. Arranque -- Diseno Funcional, Seccion 4.1
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cargar_estado()
    print(f"SOM API Demo v2 escuchando en el puerto {PORT}")
    print(f"Documentacion:  http://localhost:{PORT}{BASE}/docs")
    print(f"Acceso en red:  http://<IP_DE_ESTE_EQUIPO>:{PORT}{BASE}/ordenes")
    print(f"Datos:          {DATA_FILE}")
    print(f"Log de eventos: {LOG_FILE}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
