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

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask requests
Ejecucion:    python crm_som.py
Acceso:       http://localhost:8082/         (interfaz web)
              http://localhost:8082/estado   (estado del servicio, JSON)
"""

import os
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("PORT", 8082))
LOG_FILE = "crm_som.log"

SOM_API_URL = os.environ.get("SOM_API_URL", "http://som-api:8081/api/v1")
SOM_API_KEY = os.environ.get("SOM_API_KEY", "DUOC-CUY6142-DEMO-CRM")
WEBHOOK_SECRET_ESPERADO = os.environ.get(
    "WEBHOOK_SECRET", "DUOC-CUY6142-DEMO-WEBHOOK-SECRET"
)

HEADERS_SOM_API = {
    "X-API-Key": SOM_API_KEY,
    "Content-Type": "application/json",
}

SOM_API_TIMEOUT_SEGUNDOS = 5

TIPOS_SERVICIO_VALIDOS = ["INTERNET", "TELEFONIA", "TV"]
PRIORIDADES_VALIDAS = ["ALTA", "MEDIA", "BAJA"]

# ---------------------------------------------------------------------------
# 2. Estado local
# ---------------------------------------------------------------------------

ordenes_locales = {}
eventos_webhook = []

# ---------------------------------------------------------------------------
# 3. Registro (logging)
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
# 4. Cliente REST
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


def invocar_som_api(funcion, *args, **kwargs):
    try:
        return funcion(*args, **kwargs), None
    except requests.exceptions.RequestException as excepcion:
        registrar("SOM_API_INALCANZABLE", str(excepcion))
        return None, (
            jsonify({"error": "No se pudo contactar a som-api", "detalle": str(excepcion)}),
            502,
        )


# ---------------------------------------------------------------------------
# 5. Pagina HTML de la interfaz
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
# 6. App Flask y rutas
# ---------------------------------------------------------------------------

app = Flask(__name__)


def obtener_json_o_error():
    datos = request.get_json(silent=True)
    if datos is None:
        return None, (jsonify({"error": "El cuerpo debe ser JSON valido con Content-Type: application/json"}), 400)
    return datos, None


@app.route("/", methods=["GET"])
def interfaz():
    return PAGINA_HTML


@app.route("/estado", methods=["GET"])
def estado():
    return jsonify({
        "servicio": "crm-som",
        "ordenes_en_cache": len(ordenes_locales),
        "eventos_webhook_recibidos": len(eventos_webhook),
        "som_api_url": SOM_API_URL,
    }), 200


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


@app.route("/ordenes", methods=["GET"])
def listar_ordenes():
    respuesta, error = invocar_som_api(som_api_listar_ordenes)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        for orden in respuesta.json():
            ordenes_locales[orden["id"]] = orden

    return jsonify(respuesta.json()), respuesta.status_code


@app.route("/ordenes/<id_orden>", methods=["GET"])
def obtener_orden(id_orden):
    respuesta, error = invocar_som_api(som_api_obtener_orden, id_orden)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()

    return jsonify(respuesta.json()), respuesta.status_code


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


@app.route("/ordenes/<id_orden>", methods=["DELETE"])
def cancelar_orden(id_orden):
    respuesta, error = invocar_som_api(som_api_cancelar_orden, id_orden)
    if error is not None:
        return error

    if respuesta.status_code == 200:
        ordenes_locales[id_orden] = respuesta.json()
        registrar("ORDEN_CANCELADA", f"id={id_orden}")

    return jsonify(respuesta.json()), respuesta.status_code


@app.route("/eventos", methods=["GET"])
def listar_eventos():
    return jsonify(eventos_webhook), 200


@app.route("/webhooks/ordenes", methods=["POST"])
def recibir_webhook():
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

    if orden_id:
        respuesta, error = invocar_som_api(som_api_obtener_orden, orden_id)
        if error is None and respuesta.status_code == 200:
            ordenes_locales[orden_id] = respuesta.json()

    return jsonify({"recibido": True}), 200


if __name__ == "__main__":
    print(f"crm-som escuchando en el puerto {PORT}")
    print(f"Interfaz web:   http://localhost:{PORT}/")
    print(f"Estado (JSON):  http://localhost:{PORT}/estado")
    print(f"som-api configurada en: {SOM_API_URL}")
    print(f"Log de eventos: {LOG_FILE}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
