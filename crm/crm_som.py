"""
crm_som.py

Plataforma de gestion (CRM) para la Orden de Servicio -- consume la API
som_api_demo por el canal CRM (Contrato Operativo v1.3, Seccion 4) y actua
ademas como receptor de sus notificaciones asincronas (webhook, Seccion 6).
Incluye una interfaz web propia: a diferencia de som_api_demo.py, este
servicio no se recorre en clase linea a linea -- se ejecuta dockerizado y
se usa como una caja negra, para mostrar la comunicacion entre sistemas via
API (peticion sincrona + notificacion asincrona), no la implementacion.

Alcance de este canal, por decision de diseno: el CRM crea, lista, consulta,
edita (PUT) y cancela (DELETE) ordenes. No transiciona estado (PATCH) --
esa operacion queda reservada al canal GUI (Postman). Tambien recibe el
webhook de cambio de estado y refresca su vista local cuando llega, sea cual
sea el canal que origino el cambio.

Autoregistro de webhook (uso exclusivo del entorno de trabajo propio -- no
forma parte del material entregado a estudiantes): al arrancar, este
servicio intenta registrarse a si mismo como receptor de notificaciones en
som-api (POST /webhooks, Seccion 6.2 del Contrato Operativo), para no
depender del paso manual "Registrar webhook" de la coleccion Postman. El
Contrato Operativo no restringe ese endpoint por canal -- cualquier
X-API-Key valida sirve -- por lo que usar la clave CRM ya presente en este
archivo es valido. Ver autoregistrar_webhook() en la Seccion 7.

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask requests
Ejecucion:    python crm_som.py
Acceso:       http://localhost:8082/         (interfaz web)
              http://localhost:8082/estado   (estado del servicio, JSON)
"""

import os
import threading
import time
from datetime import datetime, timezone

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

# URL propia con la que este servicio se autoregistra en som-api -- debe ser
# alcanzable DESDE som-api, no desde el equipo del docente. Dentro de
# som-network se resuelve por nombre de contenedor (default). Fuera de
# Docker (ejecucion local, Escenario C de Validacion_Local_OrdenServicio.md)
# se sobrescribe con la variable de entorno WEBHOOK_URL_PROPIA.
WEBHOOK_URL_PROPIA = os.environ.get(
    "WEBHOOK_URL_PROPIA", f"http://crm-som:{PORT}/webhooks/ordenes"
)

# Reintentos del autoregistro -- som-api puede no estar listo todavia cuando
# arranca este proceso (docker compose solo garantiza orden de inicio de
# contenedores, no que la app Flask ya este escuchando).
WEBHOOK_AUTOREGISTRO_INTENTOS = int(os.environ.get("WEBHOOK_AUTOREGISTRO_INTENTOS", 10))
WEBHOOK_AUTOREGISTRO_ESPERA_SEGUNDOS = int(
    os.environ.get("WEBHOOK_AUTOREGISTRO_ESPERA_SEGUNDOS", 2)
)

# Dominios de valores del recurso -- Contrato de Datos, Seccion 3. Se
# repiten aqui solo para poblar los `select` del formulario; la validacion
# real la sigue haciendo som-api (Seccion 4 del Contrato de Datos).
TIPOS_SERVICIO_VALIDOS = ["INTERNET", "TELEFONIA", "TV"]
PRIORIDADES_VALIDAS = ["ALTA", "MEDIA", "BAJA"]

# ---------------------------------------------------------------------------
# 2. Estado local -- vista que el CRM mantiene en memoria, actualizada por
#    las respuestas de sus propias llamadas y por los webhooks entrantes.
#    No reemplaza a som-api como fuente de verdad: es una cache de lectura
#    para la interfaz, reconciliable en cualquier momento contra GET
#    /ordenes. Se pierde al reiniciar el proceso, mismo criterio de
#    simplicidad que el estado en memoria de som-api.
# ---------------------------------------------------------------------------

ordenes_locales = {}

# Historial de notificaciones de webhook recibidas -- no es parte del
# Contrato Operativo (es estado interno de crm-som, no de som-api).
# Alimenta el panel de la interfaz que muestra la respuesta asincrona
# llegando sin que el usuario la solicite.
eventos_webhook = []

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


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 4. Cliente REST -- llamadas hacia som-api, canal CRM. Cubre las cinco
#    operaciones que son prerrogativa del CRM: crear, listar, consultar,
#    editar (PUT) y cancelar (DELETE). PATCH queda deliberadamente fuera.
#    som_api_registrar_webhook() es la excepcion: no es una operacion del
#    canal CRM segun el Contrato Operativo (que no distingue canal para ese
#    endpoint) -- se agrega aqui solo para el autoregistro (Seccion 7).
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


def som_api_registrar_webhook(url_propia):
    return requests.post(
        f"{SOM_API_URL}/webhooks",
        json={"url": url_propia},
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


def invocar_som_api(funcion, *args, **kwargs):
    """Ejecuta una llamada al cliente REST de som-api, traduciendo un fallo
    de conexion (som-api caido, inalcanzable, o timeout) en una respuesta
    502 legible para la interfaz, en vez de una excepcion no controlada
    que rompe la demo sin explicacion.

    Devuelve (respuesta, None) si la llamada se completo -- con el codigo
    HTTP que sea, incluido un error de som-api, que no es asunto de esta
    funcion -- o (None, (cuerpo_json, 502)) si la llamada ni siquiera pudo
    realizarse. Este 502 es una decision propia de crm-som, no forma parte
    del Contrato Operativo (ese contrato define los codigos que devuelve
    som-api, no los que genera un cliente suyo).
    """
    try:
        return funcion(*args, **kwargs), None
    except requests.exceptions.RequestException as excepcion:
        registrar("SOM_API_INALCANZABLE", str(excepcion))
        return None, (
            jsonify({"error": "No se pudo contactar a som-api", "detalle": str(excepcion)}),
            502,
        )


# ---------------------------------------------------------------------------
# 5. Pagina HTML de la interfaz -- autocontenida (CSS y JS inline, sin
#    dependencias externas). No usa plantillas Jinja porque no hay datos
#    que el servidor deba incrustar: la pagina carga todo su contenido via
#    `fetch` a los mismos endpoints JSON de la Seccion 6, igual que lo
#    haria Postman o `curl` -- la interfaz es un cliente mas de esos
#    endpoints, no un camino distinto.
# ---------------------------------------------------------------------------

PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>crm-som</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: Lato, Calibri, sans-serif;
    margin: 0;
    background: #F4F6F8;
    color: #1A1A1A;
  }
  header {
    background: #1A1A1A;
    color: #FFFFFF;
    padding: 20px 32px;
    border-bottom: 4px solid #307FE2;
  }
  header h1 {
    margin: 0;
    font-family: Merriweather, Georgia, serif;
    font-size: 1.4em;
  }
  header p {
    margin: 4px 0 0 0;
    color: #8BB8E8;
    font-size: 0.9em;
  }
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 24px 32px 64px 32px;
  }
  section {
    background: #FFFFFF;
    border: 1px solid #D8DDE3;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 24px;
  }
  h2 {
    margin-top: 0;
    font-size: 1.1em;
    color: #1A1A1A;
  }
  label {
    display: block;
    margin-bottom: 12px;
    font-size: 0.9em;
  }
  input, select {
    display: block;
    width: 100%;
    padding: 6px 8px;
    margin-top: 4px;
    border: 1px solid #B8C0CA;
    border-radius: 4px;
    font-size: 0.95em;
  }
  button {
    background: #307FE2;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 0.9em;
    cursor: pointer;
  }
  button:hover { background: #2568BD; }
  button.secundario { background: #6B7684; }
  button.secundario:hover { background: #545C67; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88em;
  }
  th, td {
    text-align: left;
    padding: 8px 6px;
    border-bottom: 1px solid #E2E6EA;
  }
  th { color: #545C67; font-weight: 600; }
  td button { margin-right: 4px; padding: 4px 10px; font-size: 0.85em; }
  #resultado-contenido {
    background: #1A1A1A;
    color: #D8F0D8;
    padding: 12px 16px;
    border-radius: 4px;
    font-family: "Courier New", monospace;
    font-size: 0.85em;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 260px;
    overflow-y: auto;
  }
  .nota { color: #6B7684; font-size: 0.85em; margin-top: -8px; }
  #editar { display: none; }
</style>
</head>
<body>

<header>
  <h1>crm-som -- Panel de Ordenes</h1>
  <p>Canal CRM &middot; som-api en <span id="som-api-url">...</span></p>
</header>

<main>

  <section id="crear">
    <h2>Crear orden (POST)</h2>
    <form id="form-crear">
      <label>Cliente ID
        <input name="cliente_id" required>
      </label>
      <label>Tipo de servicio
        <select name="tipo_servicio"></select>
      </label>
      <label>Prioridad
        <select name="prioridad"></select>
      </label>
      <label>Descripcion
        <input name="descripcion">
      </label>
      <button type="submit">Crear orden</button>
    </form>
  </section>

  <section id="resultado">
    <h2>Ultima operacion</h2>
    <pre id="resultado-contenido">Sin operaciones todavia.</pre>
  </section>

  <section id="ordenes">
    <h2>Ordenes <button id="btn-refrescar" class="secundario" type="button">Actualizar (GET)</button></h2>
    <table id="tabla-ordenes">
      <thead>
        <tr><th>ID</th><th>Cliente</th><th>Servicio</th><th>Prioridad</th><th>Estado</th><th>Actualizada</th><th>Acciones</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>

  <section id="editar">
    <h2>Editar orden <span id="editar-id"></span> (PUT)</h2>
    <form id="form-editar">
      <input type="hidden" name="id">
      <label>Cliente ID
        <input name="cliente_id" required>
      </label>
      <label>Tipo de servicio
        <select name="tipo_servicio"></select>
      </label>
      <label>Prioridad
        <select name="prioridad"></select>
      </label>
      <label>Descripcion
        <input name="descripcion">
      </label>
      <button type="submit">Guardar cambios</button>
      <button type="button" class="secundario" id="btn-cancelar-edicion">Cancelar edicion</button>
    </form>
  </section>

  <section id="eventos">
    <h2>Notificaciones recibidas (webhook)</h2>
    <p class="nota">Respuesta asincrona de som-api -- se actualiza sola cada 3 segundos, sin que el usuario la pida.</p>
    <table id="tabla-eventos">
      <thead>
        <tr><th>Orden</th><th>Operacion</th><th>Transicion</th><th>Canal origen</th><th>Recibido</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>

</main>

<script>
const ORDENES_URL = '/ordenes';
const EVENTOS_URL = '/eventos';
const ESTADO_URL = '/estado';
const TIPOS_SERVICIO = ['INTERNET', 'TELEFONIA', 'TV'];
const PRIORIDADES = ['ALTA', 'MEDIA', 'BAJA'];

function poblarSelect(select, opciones, seleccionado) {
  select.innerHTML = '';
  for (const opcion of opciones) {
    const el = document.createElement('option');
    el.value = opcion;
    el.textContent = opcion;
    if (opcion === seleccionado) el.selected = true;
    select.appendChild(el);
  }
}

document.querySelectorAll('select[name="tipo_servicio"]').forEach(s => poblarSelect(s, TIPOS_SERVICIO));
document.querySelectorAll('select[name="prioridad"]').forEach(s => poblarSelect(s, PRIORIDADES, 'MEDIA'));

function mostrarResultado(metodo, ruta, status, cuerpo) {
  const el = document.getElementById('resultado-contenido');
  el.textContent = metodo + ' ' + ruta + ' -> ' + status + '\\n\\n' + JSON.stringify(cuerpo, null, 2);
}

async function cargarEstado() {
  const resp = await fetch(ESTADO_URL);
  const datos = await resp.json();
  document.getElementById('som-api-url').textContent = datos.som_api_url;
}

async function cargarOrdenes() {
  const resp = await fetch(ORDENES_URL);
  const datos = await resp.json();
  mostrarResultado('GET', ORDENES_URL, resp.status, datos);
  const cuerpo = document.querySelector('#tabla-ordenes tbody');
  cuerpo.innerHTML = '';
  if (!Array.isArray(datos)) return;
  for (const orden of datos) {
    const fila = document.createElement('tr');
    fila.innerHTML =
      '<td>' + orden.id + '</td>' +
      '<td>' + orden.cliente_id + '</td>' +
      '<td>' + orden.tipo_servicio + '</td>' +
      '<td>' + orden.prioridad + '</td>' +
      '<td>' + orden.estado + '</td>' +
      '<td>' + orden.fecha_actualizacion + '</td>' +
      '<td>' +
        '<button data-accion="detalle" data-id="' + orden.id + '">Ver</button>' +
        '<button data-accion="editar" data-id="' + orden.id + '">Editar</button>' +
        '<button data-accion="cancelar" data-id="' + orden.id + '">Cancelar</button>' +
      '</td>';
    cuerpo.appendChild(fila);
  }
}

function abrirFormularioEdicion(orden) {
  const seccion = document.getElementById('editar');
  seccion.style.display = 'block';
  document.getElementById('editar-id').textContent = orden.id;
  const form = document.getElementById('form-editar');
  form.id.value = orden.id;
  form.cliente_id.value = orden.cliente_id;
  poblarSelect(form.tipo_servicio, TIPOS_SERVICIO, orden.tipo_servicio);
  poblarSelect(form.prioridad, PRIORIDADES, orden.prioridad);
  form.descripcion.value = orden.descripcion;
  seccion.scrollIntoView({ behavior: 'smooth' });
}

document.querySelector('#tabla-ordenes').addEventListener('click', async (evento) => {
  const boton = evento.target.closest('button[data-accion]');
  if (!boton) return;
  const id = boton.dataset.id;
  const accion = boton.dataset.accion;

  if (accion === 'detalle') {
    const resp = await fetch(ORDENES_URL + '/' + id);
    const datos = await resp.json();
    mostrarResultado('GET', ORDENES_URL + '/' + id, resp.status, datos);
  } else if (accion === 'editar') {
    const resp = await fetch(ORDENES_URL + '/' + id);
    const datos = await resp.json();
    mostrarResultado('GET', ORDENES_URL + '/' + id, resp.status, datos);
    if (resp.status === 200) abrirFormularioEdicion(datos);
  } else if (accion === 'cancelar') {
    if (!confirm('Cancelar la orden ' + id + '?')) return;
    const resp = await fetch(ORDENES_URL + '/' + id, { method: 'DELETE' });
    const datos = await resp.json();
    mostrarResultado('DELETE', ORDENES_URL + '/' + id, resp.status, datos);
    cargarOrdenes();
  }
});

document.getElementById('btn-cancelar-edicion').addEventListener('click', () => {
  document.getElementById('editar').style.display = 'none';
});

document.getElementById('form-crear').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const datos = {
    cliente_id: form.cliente_id.value,
    tipo_servicio: form.tipo_servicio.value,
    prioridad: form.prioridad.value,
    descripcion: form.descripcion.value,
  };
  const resp = await fetch(ORDENES_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datos),
  });
  const cuerpo = await resp.json();
  mostrarResultado('POST', ORDENES_URL, resp.status, cuerpo);
  if (resp.status === 201) form.reset();
  poblarSelect(form.tipo_servicio, TIPOS_SERVICIO);
  poblarSelect(form.prioridad, PRIORIDADES, 'MEDIA');
  cargarOrdenes();
});

document.getElementById('form-editar').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const id = form.id.value;
  const datos = {
    cliente_id: form.cliente_id.value,
    tipo_servicio: form.tipo_servicio.value,
    prioridad: form.prioridad.value,
    descripcion: form.descripcion.value,
  };
  const resp = await fetch(ORDENES_URL + '/' + id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(datos),
  });
  const cuerpo = await resp.json();
  mostrarResultado('PUT', ORDENES_URL + '/' + id, resp.status, cuerpo);
  if (resp.status === 200) document.getElementById('editar').style.display = 'none';
  cargarOrdenes();
});

document.getElementById('btn-refrescar').addEventListener('click', cargarOrdenes);

async function cargarEventos() {
  const resp = await fetch(EVENTOS_URL);
  const datos = await resp.json();
  const cuerpo = document.querySelector('#tabla-eventos tbody');
  cuerpo.innerHTML = '';
  for (const evento of [...datos].reverse()) {
    const fila = document.createElement('tr');
    fila.innerHTML =
      '<td>' + evento.orden_id + '</td>' +
      '<td>' + evento.operacion + '</td>' +
      '<td>' + evento.estado_anterior + ' -&gt; ' + evento.estado_nuevo + '</td>' +
      '<td>' + evento.canal_origen + '</td>' +
      '<td>' + evento.fecha_recepcion + '</td>';
    cuerpo.appendChild(fila);
  }
}

cargarEstado();
cargarOrdenes();
cargarEventos();
setInterval(cargarEventos, 3000);
</script>

</body>
</html>
"""

# ---------------------------------------------------------------------------
# 6. App Flask y rutas -- endpoints propios del CRM. Los cinco endpoints de
#    ordenes son proxy directo hacia som-api; la interfaz (Seccion 5) es
#    solo otro cliente de estos mismos endpoints, via `fetch`.
# ---------------------------------------------------------------------------

app = Flask(__name__)


def obtener_json_o_error():
    datos = request.get_json(silent=True)
    if datos is None:
        return None, (jsonify({"error": "El cuerpo debe ser JSON valido con Content-Type: application/json"}), 400)
    return datos, None


# --- GET / -- interfaz web ---------------------------------------------------

@app.route("/", methods=["GET"])
def interfaz():
    return PAGINA_HTML


# --- GET /estado -- estado basico del servicio (JSON) -----------------------

@app.route("/estado", methods=["GET"])
def estado():
    return jsonify({
        "servicio": "crm-som",
        "ordenes_en_cache": len(ordenes_locales),
        "eventos_webhook_recibidos": len(eventos_webhook),
        "som_api_url": SOM_API_URL,
    }), 200


# --- POST /ordenes -- crear (proxy hacia som-api) ---------------------------

@app.route("/ordenes", methods=["POST"])
def crear_orden():
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    respuesta, error = invocar_som_api(som_api_crear_orden, datos)
    if error is not None:
        return error

    if respuesta.status_code == 201:
        orden = respuesta.json()
        ordenes_locales[orden["id"]] = orden
        registrar("ORDEN_CREADA", f"id={orden['id']}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- GET /ordenes -- listar (proxy, refresca la cache local) ---------------

@app.route("/ordenes", methods=["GET"])
def listar_ordenes():
    respuesta, error = invocar_som_api(som_api_listar_ordenes)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        for orden in respuesta.json():
            ordenes_locales[orden["id"]] = orden

    return jsonify(respuesta.json()), respuesta.status_code


# --- GET /ordenes/<id_orden> -- detalle (proxy) -----------------------------

@app.route("/ordenes/<id_orden>", methods=["GET"])
def obtener_orden(id_orden):
    respuesta, error = invocar_som_api(som_api_obtener_orden, id_orden)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()

    return jsonify(respuesta.json()), respuesta.status_code


# --- PUT /ordenes/<id_orden> -- editar (proxy) ------------------------------

@app.route("/ordenes/<id_orden>", methods=["PUT"])
def editar_orden(id_orden):
    datos, error = obtener_json_o_error()
    if error is not None:
        return error

    respuesta, error = invocar_som_api(som_api_editar_orden, id_orden, datos)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()
        registrar("ORDEN_EDITADA", f"id={id_orden}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- DELETE /ordenes/<id_orden> -- cancelar (proxy) -------------------------

@app.route("/ordenes/<id_orden>", methods=["DELETE"])
def cancelar_orden(id_orden):
    respuesta, error = invocar_som_api(som_api_cancelar_orden, id_orden)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()
        registrar("ORDEN_CANCELADA", f"id={id_orden}")

    return jsonify(respuesta.json()), respuesta.status_code


# --- GET /eventos -- historial de notificaciones de webhook recibidas ------

@app.route("/eventos", methods=["GET"])
def listar_eventos():
    return jsonify(eventos_webhook), 200


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

    eventos_webhook.append({
        "orden_id": orden_id,
        "operacion": evento.get("operacion"),
        "estado_anterior": evento.get("estado_anterior"),
        "estado_nuevo": evento.get("estado_nuevo"),
        "canal_origen": evento.get("canal_origen"),
        "fecha_evento": evento.get("fecha_evento"),
        "fecha_recepcion": ahora_iso(),
    })

    # El payload del webhook es liviano por diseno (Contrato Operativo,
    # Seccion 6.5): no trae la representacion completa de la orden. En vez
    # de confiar en el estado_nuevo del evento para pintar la vista local,
    # se confirma con un GET a som-api -- coherente con el patron que el
    # propio contrato describe para el receptor. Si som-api no responde en
    # este instante, el webhook igual se registra (arriba) y se reconoce
    # con 200 -- solo se omite la actualizacion de la cache local.
    if orden_id:
        respuesta, error = invocar_som_api(som_api_obtener_orden, orden_id)
        if error is None and respuesta.status_code == 200:
            ordenes_locales[orden_id] = respuesta.json()

    return jsonify({"recibido": True}), 200


# ---------------------------------------------------------------------------
# 7. Autoregistro del webhook -- uso exclusivo del entorno de trabajo
#    propio. No es parte del Contrato Operativo ni del material entregado a
#    estudiantes (Guia Rapida / coleccion Postman), que siguen documentando
#    el registro manual via POST /webhooks (canal GUI) como el flujo de
#    referencia para la clase.
# ---------------------------------------------------------------------------


def autoregistrar_webhook():
    """Registra crm-som como receptor de notificaciones en som-api al
    arrancar (POST /webhooks, Contrato Operativo Seccion 6.2), para no
    depender del paso manual de la coleccion Postman en este entorno.

    El endpoint no distingue canal -- cualquier X-API-Key valida sirve --
    por lo que usar la clave CRM ya configurada en este archivo (Seccion 1)
    es valido segun el propio contrato (ver ejemplo de su Seccion 6.2, que
    usa esa misma clave).

    Corre en un hilo separado (ver Seccion 8, arranque) para no retrasar la
    disponibilidad de la interfaz web mientras reintenta: docker compose
    solo garantiza el orden de inicio de los contenedores, no que la app de
    som-api ya este escuchando. Si se agotan los intentos, se registra el
    fallo en el log y queda disponible el registro manual (POST /webhooks)
    como respaldo -- no es distinto de un fallo del paso manual.
    """
    for intento in range(1, WEBHOOK_AUTOREGISTRO_INTENTOS + 1):
        try:
            respuesta = som_api_registrar_webhook(WEBHOOK_URL_PROPIA)
        except requests.exceptions.RequestException as excepcion:
            registrar(
                "WEBHOOK_AUTOREGISTRO_REINTENTO",
                f"intento={intento}/{WEBHOOK_AUTOREGISTRO_INTENTOS} | som-api inalcanzable: {excepcion}",
            )
        else:
            if respuesta.status_code == 201:
                registrar("WEBHOOK_AUTOREGISTRADO", f"url={WEBHOOK_URL_PROPIA}")
                return
            registrar(
                "WEBHOOK_AUTOREGISTRO_REINTENTO",
                f"intento={intento}/{WEBHOOK_AUTOREGISTRO_INTENTOS} | som-api respondio {respuesta.status_code}",
            )
        time.sleep(WEBHOOK_AUTOREGISTRO_ESPERA_SEGUNDOS)

    registrar(
        "WEBHOOK_AUTOREGISTRO_FALLIDO",
        f"agotados {WEBHOOK_AUTOREGISTRO_INTENTOS} intentos -- "
        f"registrar manualmente con POST {SOM_API_URL}/webhooks",
    )


# ---------------------------------------------------------------------------
# 8. Arranque -- threaded=True: crm-som puede recibir el webhook entrante
#    mientras tiene una llamada saliente en curso hacia som-api (por
#    ejemplo, un DELETE esperando respuesta), y mientras atiende la propia
#    interfaz web en paralelo. Sin esto, el servidor de desarrollo de
#    Flask atiende una solicitud a la vez y quedarian en interbloqueo --
#    ver la nota de diseno del webhook en el Contrato Operativo, Seccion
#    6.4. El autoregistro (Seccion 7) corre en su propio hilo daemon para
#    no retrasar app.run() mientras reintenta.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"crm-som escuchando en el puerto {PORT}")
    print(f"Interfaz web:   http://localhost:{PORT}/")
    print(f"Estado (JSON):  http://localhost:{PORT}/estado")
    print(f"som-api configurada en: {SOM_API_URL}")
    print(f"Log de eventos: {LOG_FILE}")
    threading.Thread(target=autoregistrar_webhook, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
