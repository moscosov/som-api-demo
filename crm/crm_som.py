"""
crm_som.py -- version 2.0

Plataforma de gestion (CRM) para la Orden de Servicio. Consume la API
som_api_demo version 2.x por el canal CRM y actua ademas como receptor de
sus notificaciones asincronas (webhook).

Compatible con:
  - Contrato_Datos_OrdenServicio_DuocUC.md      (version 2.0)
  - Contrato_Operativo_OrdenServicio_DuocUC.md  (version 2.1), ruta base /api/v2

Uso: demostracion docente. Se ejecuta dockerizado y se usa como caja negra,
para mostrar la comunicacion entre sistemas via API (peticion sincrona +
notificacion asincrona), no su implementacion.

Decisiones de diseno de la version 2.0:
  - Autenticacion con la clave fija del canal CRM (Contrato Operativo,
    Seccion 4.3). No usa loginViaBasic: los tokens viven en la memoria de
    som-api y se pierden cuando se reinicia; la clave fija no.
  - com_id: crm-som emite sus propios numeros de orden comercial en el
    rango reservado 9000000-9999999 (Contrato de Datos, Seccion 3.5: el
    com_id lo emite el sistema solicitante). No guarda estado propio: al
    arrancar, o tras una colision, toma el com_id mas alto registrado en
    som-api y continua desde el siguiente.
  - Alcance del canal: crea los cuatro tipos de orden, lista, consulta,
    reemplaza (PUT: prioridad y descripcion), cancela (DELETE) y consulta
    la trazabilidad. No usa PATCH: transicionar el estado queda reservado
    al canal GUI (Postman).
  - Re-registro periodico del webhook: som-api guarda el webhook solo en
    memoria. crm-som lo vuelve a registrar cada WEBHOOK_REREGISTRO_SEGUNDOS
    y en el mismo ciclo resincroniza su copia local de las ordenes.
    Consecuencia: crm-som reemplaza a cualquier otro receptor registrado en
    el mismo som-api (el contrato admite un unico webhook activo).

CUY6142 - Telepresencia y Entornos Innovadores de Colaboracion Humana

Dependencias: pip install flask requests
Ejecucion:    python crm_som.py
Acceso:       http://localhost:8082/         (interfaz web)
              http://localhost:8082/estado   (estado del servicio, JSON)
"""

import collections
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask, Response, jsonify, request

VERSION = "2.0"

# ---------------------------------------------------------------------------
# 1. Configuracion. Todo valor que cambia segun el entorno (Docker,
#    ejecucion local, Kubernetes) se puede sobrescribir con una variable de
#    entorno.
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("PORT", 8082))
LOG_FILE = "crm_som.log"

# URL base de som-api. Dentro de la red Docker se resuelve por nombre de
# contenedor (som-api). Fuera de Docker se sobrescribe con SOM_API_URL.
SOM_API_URL = os.environ.get("SOM_API_URL", "http://som-api:8081/api/v2").rstrip("/")

# Clave fija del canal CRM -- Contrato Operativo, Seccion 4.3.
SOM_API_KEY = os.environ.get("SOM_API_KEY", "DUOC-CUY6142-DEMO-CRM")

# Secreto esperado en las notificaciones entrantes -- Contrato Operativo,
# Seccion 6.6. Debe coincidir con el secreto configurado en som-api.
WEBHOOK_SECRET_ESPERADO = os.environ.get("WEBHOOK_SECRET", "DUOC-CUY6142-DEMO-WEBHOOK-SECRET")

# URL con la que crm-som se registra como receptor. Debe ser alcanzable
# DESDE som-api, no desde el equipo del docente.
WEBHOOK_URL_PROPIA = os.environ.get("WEBHOOK_URL_PROPIA", f"http://crm-som:{PORT}/webhooks/ordenes")

# Re-registro periodico del webhook y resincronizacion de la copia local.
WEBHOOK_REREGISTRO_SEGUNDOS = int(os.environ.get("WEBHOOK_REREGISTRO_SEGUNDOS", 60))
# Espera antes de reintentar cuando el registro fallo (som-api caido o
# todavia arrancando).
WEBHOOK_REINTENTO_SEGUNDOS = int(os.environ.get("WEBHOOK_REINTENTO_SEGUNDOS", 5))

SOM_API_TIMEOUT_SEGUNDOS = 5

HEADERS_SOM_API = {"X-API-KEY": SOM_API_KEY}

# Rango reservado de com_id para el canal CRM. El primer numero emitido es
# 9000001, mismo estilo que los ejemplos del Contrato de Datos (1000001).
COM_ID_MINIMO = 9000000
COM_ID_MAXIMO = 9999999
COM_ID_PRIMERO = 9000001
COM_ID_REINTENTOS = 3

# Tamano de pagina para resincronizar la copia local (maximo del contrato).
TAMANO_PAGINA_SINCRONIZACION = 100

# Cantidad maxima de notificaciones que se conservan para el panel.
EVENTOS_MAXIMO = 200

# ---------------------------------------------------------------------------
# 2. Estado local. crm-som no es la fuente de verdad: som-api lo es. Todo
#    lo que esta aqui es una copia o un dato de operacion de crm-som, y se
#    pierde al reiniciar el proceso.
# ---------------------------------------------------------------------------

# Copia local de las ordenes, actualizada por las respuestas de som-api, por
# los webhooks entrantes y por la resincronizacion periodica.
ordenes_locales = {}

# Historial de notificaciones recibidas (las mas recientes al final).
eventos_webhook = collections.deque(maxlen=EVENTOS_MAXIMO)
eventos_recibidos_total = {"valor": 0}

# Estado del registro del webhook en som-api.
registro_webhook = {
    "registrado": False,
    "ultimo_registro": None,
    "ultimo_error": None,
}

# Secuencia de com_id. None significa "sin sincronizar": el proximo uso
# consulta el com_id mas alto de som-api.
secuencia_com_id = {"siguiente": None}

# Serializa las creaciones de orden: dos solicitudes simultaneas no pueden
# tomar el mismo com_id.
candado_com_id = threading.Lock()

# ---------------------------------------------------------------------------
# 3. Registro (logging) -- mismo formato de linea en consola y archivo.
# ---------------------------------------------------------------------------


def registrar(evento, detalle=""):
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca_tiempo}] {evento}"
    if detalle:
        linea += f" | {detalle}"
    print(linea, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(linea + "\n")


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def error_propio(codigo_http, codigo, mensaje):
    """Error generado por crm-som (no por som-api). Usa el mismo formato
    estandarizado del Contrato Operativo, Seccion 7, para que la interfaz
    trate igual los errores de ambos servicios."""
    registrar("ERROR", f"{codigo_http} {codigo} - {mensaje}")
    return jsonify({"error": {"codigo": codigo, "mensaje": mensaje}}), codigo_http


# ---------------------------------------------------------------------------
# 4. Cliente REST hacia som-api (canal CRM)
# ---------------------------------------------------------------------------


def llamar_som(metodo, ruta, params=None, cuerpo=None):
    """Una solicitud a som-api con la clave del canal CRM. Lanza
    requests.exceptions.RequestException si som-api no responde."""
    return requests.request(
        metodo,
        f"{SOM_API_URL}{ruta}",
        params=params,
        json=cuerpo,
        headers=HEADERS_SOM_API,
        timeout=SOM_API_TIMEOUT_SEGUNDOS,
    )


class SomInalcanzable(Exception):
    pass


def llamar_som_o_fallar(metodo, ruta, params=None, cuerpo=None):
    try:
        return llamar_som(metodo, ruta, params=params, cuerpo=cuerpo)
    except requests.exceptions.RequestException as excepcion:
        registrar("SOM_API_INALCANZABLE", str(excepcion))
        raise SomInalcanzable(str(excepcion)) from excepcion


def codigo_error(respuesta):
    """codigo del formato de error estandarizado, o None."""
    try:
        return respuesta.json()["error"]["codigo"]
    except (ValueError, KeyError, TypeError):
        return None


def respuesta_desde_som(respuesta):
    """Devuelve al navegador la respuesta de som-api tal como llego: mismo
    codigo HTTP, mismo cuerpo y el header X-Total-Count de los listados.
    crm-som es un proxy: no reinterpreta las respuestas."""
    salida = Response(
        respuesta.content,
        status=respuesta.status_code,
        content_type=respuesta.headers.get("Content-Type", "application/json"),
    )
    if "X-Total-Count" in respuesta.headers:
        salida.headers["X-Total-Count"] = respuesta.headers["X-Total-Count"]
    return salida


def guardar_en_copia_local(orden):
    if isinstance(orden, dict) and "id" in orden:
        copia = dict(orden)
        copia.pop("notificacion_webhook", None)
        ordenes_locales[orden["id"]] = copia


def parametros_de_consulta():
    """Parametros de la URL recibida, incluidos los repetidos
    (estado=RECIBIDA&estado=EN_PROGRESO), para reenviarlos a som-api."""
    return list(request.args.items(multi=True))


# ---------------------------------------------------------------------------
# 5. Secuencia de com_id (rango reservado 9000000-9999999)
# ---------------------------------------------------------------------------


def sincronizar_secuencia():
    """Toma el com_id mas alto registrado en som-api. Como el rango del CRM
    es el mas alto posible (7 digitos), si existe algun com_id del rango, el
    mas alto de som-api es el ultimo que emitio crm-som (o uno digitado a
    mano en el rango, que tambien se debe saltar). Se llama con
    candado_com_id tomado."""
    respuesta = llamar_som_o_fallar(
        "GET", "/ordenes", params={"sortBy": "com_id", "order": "desc", "size": 1}
    )
    if respuesta.status_code != 200:
        registrar("COM_ID_NO_SINCRONIZADO", f"som-api respondio {respuesta.status_code} ({codigo_error(respuesta)})")
        return False
    ordenes = respuesta.json()
    siguiente = COM_ID_PRIMERO
    if ordenes:
        maximo = int(ordenes[0]["com_id"])
        if maximo >= COM_ID_MINIMO:
            siguiente = maximo + 1
    secuencia_com_id["siguiente"] = siguiente
    registrar("COM_ID_SINCRONIZADO", f"siguiente={siguiente:07d}")
    return True


# ---------------------------------------------------------------------------
# 6. Pagina HTML de la interfaz. Autocontenida (CSS y JavaScript en linea,
#    sin dependencias externas). La pagina es un cliente mas de los
#    endpoints JSON de la Seccion 7: usa fetch igual que lo haria Postman.
# ---------------------------------------------------------------------------

PAGINA_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>crm-som</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: Lato, Calibri, sans-serif; margin: 0; background: #F4F6F8; color: #1A1A1A; }
  header { background: #1A1A1A; color: #FFFFFF; padding: 18px 32px; border-bottom: 4px solid #307FE2; }
  header h1 { margin: 0; font-family: Merriweather, Georgia, serif; font-size: 1.35em; }
  header p { margin: 4px 0 0 0; color: #8BB8E8; font-size: 0.9em; }
  .indicador { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 0.85em; }
  .indicador.ok { background: #1F7A3A; color: #FFFFFF; }
  .indicador.mal { background: #A12A2A; color: #FFFFFF; }
  main { max-width: 1180px; margin: 0 auto; padding: 24px 32px 64px 32px; }
  section { background: #FFFFFF; border: 1px solid #D8DDE3; border-radius: 6px; padding: 18px 22px;
            margin-bottom: 22px; }
  h2 { margin-top: 0; font-size: 1.08em; }
  h3 { font-size: 0.98em; margin: 16px 0 8px 0; }
  .fila { display: flex; flex-wrap: wrap; gap: 12px; }
  .fila > label { flex: 1 1 180px; }
  label { display: block; margin-bottom: 12px; font-size: 0.88em; }
  input, select { display: block; width: 100%; padding: 6px 8px; margin-top: 4px; border: 1px solid #B8C0CA;
                  border-radius: 4px; font-size: 0.95em; background: #FFFFFF; }
  fieldset { border: 1px solid #D8DDE3; border-radius: 4px; margin: 0 0 12px 0; padding: 8px 12px 0 12px; }
  legend { font-size: 0.88em; color: #545C67; }
  button { background: #307FE2; color: #FFFFFF; border: none; border-radius: 4px; padding: 7px 14px;
           font-size: 0.88em; cursor: pointer; }
  button:hover { background: #2568BD; }
  button:disabled { background: #B8C0CA; cursor: default; }
  button.secundario { background: #6B7684; }
  button.secundario:hover { background: #545C67; }
  button.peligro { background: #A12A2A; }
  button.peligro:disabled { background: #B8C0CA; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
  th, td { text-align: left; padding: 7px 6px; border-bottom: 1px solid #E2E6EA; vertical-align: top; }
  th { color: #545C67; font-weight: 600; }
  td button { margin: 0 4px 4px 0; padding: 3px 9px; font-size: 0.82em; }
  pre { background: #1A1A1A; color: #D8F0D8; padding: 12px 16px; border-radius: 4px;
        font-family: "Courier New", monospace; font-size: 0.82em; white-space: pre-wrap;
        word-break: break-word; max-height: 280px; overflow-y: auto; margin: 0; }
  .nota { color: #6B7684; font-size: 0.85em; margin: -4px 0 12px 0; }
  .paginacion { display: flex; align-items: center; gap: 10px; margin-top: 12px; font-size: 0.88em; }
  .oculto { display: none; }
  .mono { font-family: "Courier New", monospace; }
</style>
</head>
<body>

<header>
  <h1>crm-som v2.0 -- Panel de Ordenes</h1>
  <p>Canal CRM &middot; som-api en <span id="som-api-url" class="mono">...</span> &middot;
     webhook <span id="estado-webhook" class="indicador mal">sin datos</span></p>
</header>

<main>

  <section id="crear">
    <h2>Crear orden (POST)</h2>
    <p class="nota">El com_id lo asigna crm-som, en el rango reservado para el canal CRM (9000000 a 9999999).</p>
    <form id="form-crear" autocomplete="off">
      <div class="fila">
        <label>Tipo de orden
          <select name="tipo_orden" id="crear-tipo"></select>
        </label>
        <label>Cliente ID
          <input name="cliente_id" id="crear-cliente" required>
        </label>
      </div>

      <div class="fila">
        <label id="grupo-servicio">Tipo de servicio
          <select name="tipo_servicio" id="crear-servicio"></select>
        </label>
        <label id="grupo-suscripcion">Suscripcion (ACTIVA, del cliente)
          <select name="subscription_id" id="crear-suscripcion"></select>
        </label>
        <label id="grupo-oferta">Oferta
          <select name="offer_id" id="crear-oferta"></select>
        </label>
      </div>

      <div id="grupo-puntos" class="fila">
        <fieldset style="flex: 1 1 300px">
          <legend>Punto actual (metros)</legend>
          <div class="fila">
            <label>x <input name="actual_x" type="number" step="any" min="0" max="100"></label>
            <label>y <input name="actual_y" type="number" step="any" min="0" max="100"></label>
            <label>Referencia <input name="actual_ref" maxlength="40"></label>
          </div>
        </fieldset>
        <fieldset style="flex: 1 1 300px">
          <legend>Punto de destino (metros)</legend>
          <div class="fila">
            <label>x <input name="destino_x" type="number" step="any" min="0" max="100"></label>
            <label>y <input name="destino_y" type="number" step="any" min="0" max="100"></label>
            <label>Referencia <input name="destino_ref" maxlength="40"></label>
          </div>
        </fieldset>
      </div>

      <div class="fila">
        <label>Prioridad
          <select name="prioridad" id="crear-prioridad"></select>
        </label>
        <label style="flex: 3 1 300px">Descripcion
          <input name="descripcion">
        </label>
      </div>
      <button type="submit">Crear orden</button>
    </form>
  </section>

  <section id="resultado">
    <h2>Ultima operacion</h2>
    <pre id="resultado-contenido">Sin operaciones todavia.</pre>
  </section>

  <section id="ordenes">
    <h2>Ordenes (GET)</h2>
    <div class="fila">
      <label>Tipo de orden <select id="filtro-tipo"></select></label>
      <label>Estado <select id="filtro-estado"></select></label>
      <label>Cliente ID <input id="filtro-cliente"></label>
      <label>Por pagina <select id="filtro-size"></select></label>
    </div>
    <button id="btn-buscar" type="button" class="secundario">Buscar</button>
    <p class="nota" style="margin-top: 10px">La tabla se actualiza sola cuando llega una notificacion de som-api.</p>
    <table id="tabla-ordenes">
      <thead>
        <tr><th>com_id</th><th>Tipo</th><th>Cliente</th><th>Servicio</th><th>Suscripcion</th>
            <th>Prioridad</th><th>Estado</th><th>Actualizada (UTC)</th><th>Acciones</th></tr>
      </thead>
      <tbody></tbody>
    </table>
    <div class="paginacion">
      <button id="btn-anterior" type="button" class="secundario">Anterior</button>
      <span id="texto-pagina"></span>
      <button id="btn-siguiente" type="button" class="secundario">Siguiente</button>
    </div>
  </section>

  <section id="editar" class="oculto">
    <h2>Editar orden <span id="editar-com-id" class="mono"></span> (PUT)</h2>
    <p class="nota">Solo prioridad y descripcion son editables. El resto de los campos es inmutable.</p>
    <form id="form-editar">
      <input type="hidden" name="id">
      <div class="fila">
        <label>Prioridad <select name="prioridad" id="editar-prioridad"></select></label>
        <label style="flex: 3 1 300px">Descripcion <input name="descripcion"></label>
      </div>
      <button type="submit">Guardar cambios</button>
      <button type="button" class="secundario" id="btn-cerrar-edicion">Cerrar</button>
    </form>
  </section>

  <section id="trazabilidad" class="oculto">
    <h2>Trazabilidad de la orden <span id="traza-com-id" class="mono"></span></h2>
    <div class="fila">
      <label style="flex: 0 1 160px">Idioma <select id="traza-idioma"></select></label>
    </div>
    <h3>Historial de estados</h3>
    <table id="tabla-historial">
      <thead><tr><th>Estado</th><th>Fecha (UTC)</th></tr></thead>
      <tbody></tbody>
    </table>
    <div id="traza-trabajo" class="oculto">
      <h3>Trabajo de relocalizacion: <span id="traza-resumen"></span></h3>
      <table id="tabla-pasos">
        <thead><tr><th>Paso</th><th>Instruccion</th><th>Metros</th><th>Duracion</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <p style="margin-top: 14px"><button type="button" class="secundario" id="btn-cerrar-traza">Cerrar</button></p>
  </section>

  <section id="eventos">
    <h2>Notificaciones recibidas (webhook)</h2>
    <p class="nota">Respuesta asincrona de som-api: aparece sola, sin que nadie la pida. Se revisa cada 3 segundos.</p>
    <table id="tabla-eventos">
      <thead>
        <tr><th>com_id</th><th>Tipo</th><th>Suscripcion</th><th>Operacion</th><th>Transicion</th>
            <th>Canal origen</th><th>Recibido (UTC)</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </section>

</main>

<script>
const TIPOS_ORDEN = ['ALTA', 'BAJA', 'CAMBIO_OFERTA', 'RELOCALIZACION'];
const TIPOS_SERVICIO = ['INTERNET', 'TELEFONIA', 'TV'];
const PRIORIDADES = ['ALTA', 'MEDIA', 'BAJA'];
const ESTADOS_ORDEN = ['RECIBIDA', 'EN_PROGRESO', 'COMPLETADA', 'CANCELADA'];
const TERMINALES = ['COMPLETADA', 'CANCELADA'];

const vista = { page: 1, total: 0, eventos: -1, trazaId: null };

function escapar(valor) {
  if (valor === null || valor === undefined) return '';
  return String(valor).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;');
}

function poblarSelect(select, opciones, seleccionado) {
  select.innerHTML = '';
  for (const opcion of opciones) {
    const el = document.createElement('option');
    if (Array.isArray(opcion)) { el.value = opcion[0]; el.textContent = opcion[1]; }
    else { el.value = opcion; el.textContent = opcion; }
    if (el.value === seleccionado) el.selected = true;
    select.appendChild(el);
  }
}

async function pedir(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (cuerpo !== undefined) {
    opciones.headers['Content-Type'] = 'application/json';
    opciones.body = JSON.stringify(cuerpo);
  }
  const resp = await fetch(ruta, opciones);
  const texto = await resp.text();
  let datos = texto;
  try { datos = JSON.parse(texto); } catch (e) { /* respuesta que no es JSON */ }
  const total = resp.headers.get('X-Total-Count');
  return { status: resp.status, datos: datos, total: total === null ? null : Number(total) };
}

function mostrarResultado(metodo, ruta, r, cuerpoEnviado) {
  let texto = metodo + ' ' + ruta + ' -> ' + r.status;
  if (r.total !== null) texto += '   (X-Total-Count: ' + r.total + ')';
  if (cuerpoEnviado !== undefined) texto += '\n\nEnviado:\n' + JSON.stringify(cuerpoEnviado, null, 2);
  texto += '\n\nRespuesta:\n' + (typeof r.datos === 'string' ? r.datos : JSON.stringify(r.datos, null, 2));
  document.getElementById('resultado-contenido').textContent = texto;
}

function duracionTexto(ms) {
  const s = Math.round(ms / 1000);
  const h = String(Math.floor(s / 3600)).padStart(2, '0');
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return h + ':' + m + ':' + ss + ' (' + ms + ' ms)';
}

/* ---- Formulario de creacion ---- */

const CAMPOS_POR_TIPO = {
  ALTA: ['grupo-servicio', 'grupo-oferta'],
  BAJA: ['grupo-suscripcion'],
  CAMBIO_OFERTA: ['grupo-suscripcion', 'grupo-oferta'],
  RELOCALIZACION: ['grupo-suscripcion', 'grupo-puntos'],
};

async function cargarOfertas(servicio) {
  const select = document.getElementById('crear-oferta');
  if (!servicio) { poblarSelect(select, [['', 'Elija primero una suscripcion']]); return; }
  const r = await pedir('GET', '/ofertas?tipo_servicio=' + encodeURIComponent(servicio));
  if (r.status !== 200) { poblarSelect(select, [['', 'No se pudo leer el catalogo']]); return; }
  poblarSelect(select, r.datos.map(o => [o.offer_id, o.offer_id + ' - ' + o.nombre]));
}

async function cargarSuscripciones() {
  const select = document.getElementById('crear-suscripcion');
  const cliente = document.getElementById('crear-cliente').value.trim();
  if (!cliente) { poblarSelect(select, [['', 'Ingrese primero el Cliente ID']]); return; }
  const r = await pedir('GET', '/suscripciones?estado=ACTIVA&size=100&cliente_id=' + encodeURIComponent(cliente));
  if (r.status !== 200 || r.datos.length === 0) {
    poblarSelect(select, [['', 'El cliente no tiene suscripciones ACTIVA']]);
  } else {
    select.innerHTML = '';
    for (const s of r.datos) {
      const el = document.createElement('option');
      el.value = s.subscription_id;
      el.dataset.servicio = s.tipo_servicio;
      el.textContent = s.subscription_id + ' - ' + s.tipo_servicio + ' - oferta ' + s.offer_id;
      select.appendChild(el);
    }
  }
  if (document.getElementById('crear-tipo').value === 'CAMBIO_OFERTA') await cargarOfertasDeSuscripcion();
}

async function cargarOfertasDeSuscripcion() {
  const select = document.getElementById('crear-suscripcion');
  const opcion = select.options[select.selectedIndex];
  await cargarOfertas(opcion && opcion.dataset.servicio ? opcion.dataset.servicio : null);
}

async function actualizarFormulario() {
  const tipo = document.getElementById('crear-tipo').value;
  for (const grupo of ['grupo-servicio', 'grupo-suscripcion', 'grupo-oferta', 'grupo-puntos']) {
    document.getElementById(grupo).classList.toggle('oculto', !CAMPOS_POR_TIPO[tipo].includes(grupo));
  }
  if (tipo === 'ALTA') await cargarOfertas(document.getElementById('crear-servicio').value);
  else await cargarSuscripciones();
}

function numeroOVacio(valor) {
  return valor === '' ? valor : Number(valor);
}

function punto(form, prefijo) {
  const p = { x: numeroOVacio(form[prefijo + '_x'].value), y: numeroOVacio(form[prefijo + '_y'].value) };
  const ref = form[prefijo + '_ref'].value.trim();
  if (ref) p.referencia = ref;
  return p;
}

document.getElementById('form-crear').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const tipo = form.tipo_orden.value;
  const datos = { tipo_orden: tipo, cliente_id: form.cliente_id.value.trim() };
  if (tipo === 'ALTA') datos.tipo_servicio = form.tipo_servicio.value;
  if (tipo !== 'ALTA') datos.subscription_id = form.subscription_id.value;
  if (tipo === 'ALTA' || tipo === 'CAMBIO_OFERTA') datos.offer_id = form.offer_id.value;
  if (tipo === 'RELOCALIZACION') {
    datos.punto_actual = punto(form, 'actual');
    datos.punto_destino = punto(form, 'destino');
  }
  datos.prioridad = form.prioridad.value;
  if (form.descripcion.value.trim()) datos.descripcion = form.descripcion.value.trim();

  const r = await pedir('POST', '/ordenes', datos);
  mostrarResultado('POST', '/ordenes', r, datos);
  if (r.status === 201) {
    form.descripcion.value = '';
    vista.page = 1;
    await cargarOrdenes();
    if (tipo !== 'ALTA') await cargarSuscripciones();
  }
});

/* ---- Listado ---- */

function urlListado() {
  const p = new URLSearchParams();
  p.set('sortBy', 'fecha_creacion');
  p.set('order', 'desc');
  p.set('page', vista.page);
  p.set('size', document.getElementById('filtro-size').value);
  const tipo = document.getElementById('filtro-tipo').value;
  const estado = document.getElementById('filtro-estado').value;
  const cliente = document.getElementById('filtro-cliente').value.trim();
  if (tipo) p.set('tipo_orden', tipo);
  if (estado) p.set('estado', estado);
  if (cliente) p.set('cliente_id', cliente);
  return '/ordenes?' + p.toString();
}

async function cargarOrdenes(mostrar) {
  const ruta = urlListado();
  const r = await pedir('GET', ruta);
  if (mostrar) mostrarResultado('GET', ruta, r);
  const cuerpo = document.querySelector('#tabla-ordenes tbody');
  cuerpo.innerHTML = '';
  if (r.status !== 200 || !Array.isArray(r.datos)) {
    if (!mostrar) mostrarResultado('GET', ruta, r);
    return;
  }
  for (const o of r.datos) {
    const terminal = TERMINALES.includes(o.estado);
    const fila = document.createElement('tr');
    fila.innerHTML =
      '<td class="mono">' + escapar(o.com_id) + '</td>' +
      '<td>' + escapar(o.tipo_orden) + '</td>' +
      '<td>' + escapar(o.cliente_id) + '</td>' +
      '<td>' + escapar(o.tipo_servicio) + '</td>' +
      '<td class="mono">' + escapar(o.subscription_id) + '</td>' +
      '<td>' + escapar(o.prioridad) + '</td>' +
      '<td>' + escapar(o.estado) + '</td>' +
      '<td>' + escapar(o.fecha_actualizacion) + '</td>' +
      '<td>' +
        '<button data-accion="detalle" data-id="' + escapar(o.id) + '">Ver</button>' +
        '<button data-accion="traza" data-id="' + escapar(o.id) + '">Trazabilidad</button>' +
        '<button data-accion="editar" data-id="' + escapar(o.id) + '"' +
          (terminal ? ' disabled' : '') + '>Editar</button>' +
        '<button data-accion="cancelar" data-id="' + escapar(o.id) + '" data-com="' + escapar(o.com_id) + '"' +
          ' class="peligro"' + (terminal ? ' disabled' : '') + '>Cancelar</button>' +
      '</td>';
    cuerpo.appendChild(fila);
  }
  vista.total = r.total === null ? r.datos.length : r.total;
  const size = Number(document.getElementById('filtro-size').value);
  const paginas = Math.max(1, Math.ceil(vista.total / size));
  document.getElementById('texto-pagina').textContent =
    'Pagina ' + vista.page + ' de ' + paginas + ' - ' + vista.total + ' ordenes en total';
  document.getElementById('btn-anterior').disabled = vista.page <= 1;
  document.getElementById('btn-siguiente').disabled = vista.page >= paginas;
}

document.querySelector('#tabla-ordenes').addEventListener('click', async (evento) => {
  const boton = evento.target.closest('button[data-accion]');
  if (!boton) return;
  const id = boton.dataset.id;
  const ruta = '/ordenes/' + encodeURIComponent(id);
  const accion = boton.dataset.accion;

  if (accion === 'detalle') {
    const r = await pedir('GET', ruta + '?includeOferta=true');
    mostrarResultado('GET', ruta + '?includeOferta=true', r);
  } else if (accion === 'editar') {
    const r = await pedir('GET', ruta);
    mostrarResultado('GET', ruta, r);
    if (r.status === 200) abrirEdicion(r.datos);
  } else if (accion === 'traza') {
    vista.trazaId = id;
    await cargarTrazabilidad();
  } else if (accion === 'cancelar') {
    if (!confirm('Cancelar la orden ' + boton.dataset.com + '?')) return;
    const r = await pedir('DELETE', ruta);
    mostrarResultado('DELETE', ruta, r);
    await cargarOrdenes();
  }
});

document.getElementById('btn-buscar').addEventListener('click', () => { vista.page = 1; cargarOrdenes(true); });
document.getElementById('btn-anterior').addEventListener('click', () => { vista.page -= 1; cargarOrdenes(true); });
document.getElementById('btn-siguiente').addEventListener('click', () => { vista.page += 1; cargarOrdenes(true); });

/* ---- Edicion (PUT) ---- */

function abrirEdicion(orden) {
  const seccion = document.getElementById('editar');
  seccion.classList.remove('oculto');
  document.getElementById('editar-com-id').textContent = orden.com_id;
  const form = document.getElementById('form-editar');
  form.id.value = orden.id;
  poblarSelect(form.prioridad, PRIORIDADES, orden.prioridad);
  form.descripcion.value = orden.descripcion;
  seccion.scrollIntoView({ behavior: 'smooth' });
}

document.getElementById('form-editar').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.target;
  const ruta = '/ordenes/' + encodeURIComponent(form.id.value);
  const datos = { prioridad: form.prioridad.value, descripcion: form.descripcion.value };
  const r = await pedir('PUT', ruta, datos);
  mostrarResultado('PUT', ruta, r, datos);
  if (r.status === 200) document.getElementById('editar').classList.add('oculto');
  await cargarOrdenes();
});

document.getElementById('btn-cerrar-edicion').addEventListener('click', () => {
  document.getElementById('editar').classList.add('oculto');
});

/* ---- Trazabilidad ---- */

async function cargarTrazabilidad() {
  if (!vista.trazaId) return;
  const idioma = document.getElementById('traza-idioma').value;
  const ruta = '/ordenes/' + encodeURIComponent(vista.trazaId) + '/trazabilidad?idioma=' + idioma;
  const r = await pedir('GET', ruta);
  mostrarResultado('GET', ruta, r);
  if (r.status !== 200) return;
  const t = r.datos;
  const seccion = document.getElementById('trazabilidad');
  seccion.classList.remove('oculto');
  document.getElementById('traza-com-id').textContent = t.com_id + ' (' + t.tipo_orden + ')';
  const historial = document.querySelector('#tabla-historial tbody');
  historial.innerHTML = '';
  for (const h of t.historial) {
    const fila = document.createElement('tr');
    fila.innerHTML = '<td>' + escapar(h.estado) + '</td><td>' + escapar(h.fecha) + '</td>';
    historial.appendChild(fila);
  }
  const trabajo = document.getElementById('traza-trabajo');
  trabajo.classList.toggle('oculto', !t.trabajo);
  if (t.trabajo) {
    document.getElementById('traza-resumen').textContent =
      t.trabajo.distancia_m + ' m de cable, ' + duracionTexto(t.trabajo.duracion_estimada_ms);
    const pasos = document.querySelector('#tabla-pasos tbody');
    pasos.innerHTML = '';
    for (const p of t.trabajo.pasos) {
      const fila = document.createElement('tr');
      fila.innerHTML = '<td>' + escapar(p.secuencia) + '</td><td>' + escapar(p.texto) + '</td><td>' +
        escapar(p.distancia_m) + '</td><td>' + escapar(duracionTexto(p.duracion_ms)) + '</td>';
      pasos.appendChild(fila);
    }
  }
  seccion.scrollIntoView({ behavior: 'smooth' });
}

document.getElementById('traza-idioma').addEventListener('change', cargarTrazabilidad);
document.getElementById('btn-cerrar-traza').addEventListener('click', () => {
  document.getElementById('trazabilidad').classList.add('oculto');
  vista.trazaId = null;
});

/* ---- Estado del servicio y notificaciones ---- */

async function cargarEstado() {
  try {
    const r = await pedir('GET', '/estado');
    document.getElementById('som-api-url').textContent = r.datos.som_api_url;
    const indicador = document.getElementById('estado-webhook');
    const ok = r.datos.webhook.registrado;
    indicador.textContent = ok ? 'registrado' : 'no registrado';
    indicador.className = 'indicador ' + (ok ? 'ok' : 'mal');
  } catch (e) { /* crm-som no responde: se reintenta en el proximo ciclo */ }
}

async function cargarEventos() {
  let r;
  try { r = await pedir('GET', '/eventos'); } catch (e) { return; }
  if (r.status !== 200) return;
  const cuerpo = document.querySelector('#tabla-eventos tbody');
  cuerpo.innerHTML = '';
  for (const ev of [...r.datos.eventos].reverse()) {
    const fila = document.createElement('tr');
    fila.innerHTML =
      '<td class="mono">' + escapar(ev.com_id) + '</td>' +
      '<td>' + escapar(ev.tipo_orden) + '</td>' +
      '<td class="mono">' + escapar(ev.subscription_id) + '</td>' +
      '<td>' + escapar(ev.operacion) + '</td>' +
      '<td>' + escapar(ev.estado_anterior) + ' -&gt; ' + escapar(ev.estado_nuevo) + '</td>' +
      '<td>' + escapar(ev.canal_origen) + '</td>' +
      '<td>' + escapar(ev.fecha_recepcion) + '</td>';
    cuerpo.appendChild(fila);
  }
  // Llego una notificacion nueva: se refresca la tabla de ordenes y, si esta
  // abierta, la trazabilidad.
  if (vista.eventos !== -1 && r.datos.total !== vista.eventos) {
    await cargarOrdenes();
    if (vista.trazaId) await cargarTrazabilidad();
  }
  vista.eventos = r.datos.total;
}

/* ---- Inicio ---- */

poblarSelect(document.getElementById('crear-tipo'), TIPOS_ORDEN, 'ALTA');
poblarSelect(document.getElementById('crear-servicio'), TIPOS_SERVICIO, 'INTERNET');
poblarSelect(document.getElementById('crear-prioridad'), PRIORIDADES, 'MEDIA');
poblarSelect(document.getElementById('filtro-tipo'), [['', 'Todos'], ...TIPOS_ORDEN]);
poblarSelect(document.getElementById('filtro-estado'), [['', 'Todos'], ...ESTADOS_ORDEN]);
poblarSelect(document.getElementById('filtro-size'), ['10', '20', '50', '100'], '10');
poblarSelect(document.getElementById('traza-idioma'), [['es', 'Espanol'], ['en', 'Ingles']], 'es');

document.getElementById('crear-tipo').addEventListener('change', actualizarFormulario);
document.getElementById('crear-servicio').addEventListener('change', (e) => cargarOfertas(e.target.value));
document.getElementById('crear-cliente').addEventListener('change', () => {
  if (document.getElementById('crear-tipo').value !== 'ALTA') cargarSuscripciones();
});
document.getElementById('crear-suscripcion').addEventListener('change', () => {
  if (document.getElementById('crear-tipo').value === 'CAMBIO_OFERTA') cargarOfertasDeSuscripcion();
});

actualizarFormulario();
cargarEstado();
cargarOrdenes();
cargarEventos();
setInterval(() => { cargarEstado(); cargarEventos(); }, 3000);
</script>

</body>
</html>
"""

# ---------------------------------------------------------------------------
# 7. App Flask y rutas propias de crm-som. Las rutas de ordenes,
#    suscripciones y ofertas son proxy hacia som-api con la clave CRM.
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.json.sort_keys = False
app.json.ensure_ascii = False


@app.errorhandler(SomInalcanzable)
def manejar_som_inalcanzable(excepcion):
    """som-api caido, inalcanzable o sin respuesta dentro del timeout. Es un
    codigo propio de crm-som: el Contrato Operativo define los codigos de
    som-api, no los de sus clientes."""
    return error_propio(502, "SOM_API_INALCANZABLE", f"No se pudo contactar a som-api: {excepcion}")


def cuerpo_json_o_error():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None, error_propio(
            400, "JSON_INVALIDO", "El cuerpo debe ser un objeto JSON con Content-Type: application/json"
        )
    return datos, None


# --- GET / -- interfaz web --------------------------------------------------

@app.route("/", methods=["GET"])
def interfaz():
    return Response(PAGINA_HTML, mimetype="text/html")


# --- GET /estado -- estado del servicio (JSON) ------------------------------

@app.route("/estado", methods=["GET"])
def estado():
    siguiente = secuencia_com_id["siguiente"]
    return jsonify({
        "servicio": "crm-som",
        "version": VERSION,
        "som_api_url": SOM_API_URL,
        "webhook": {
            "registrado": registro_webhook["registrado"],
            "url_propia": WEBHOOK_URL_PROPIA,
            "ultimo_registro": registro_webhook["ultimo_registro"],
            "ultimo_error": registro_webhook["ultimo_error"],
            "reregistro_segundos": WEBHOOK_REREGISTRO_SEGUNDOS,
        },
        "com_id": {
            "rango": f"{COM_ID_MINIMO:07d}-{COM_ID_MAXIMO:07d}",
            "siguiente": f"{siguiente:07d}" if siguiente is not None else None,
        },
        "ordenes_en_copia_local": len(ordenes_locales),
        "eventos_webhook_recibidos": eventos_recibidos_total["valor"],
    }), 200


# --- POST /ordenes -- crear, con com_id del rango CRM ------------------------

@app.route("/ordenes", methods=["POST"])
def crear_orden():
    datos, error = cuerpo_json_o_error()
    if error is not None:
        return error

    # El com_id lo emite crm-som: se descarta cualquier valor recibido.
    datos.pop("com_id", None)

    # Toda la creacion ocurre con el candado tomado: el numero solo avanza
    # cuando som-api acepta la orden, sin saltos por errores de validacion.
    with candado_com_id:
        respuesta = None
        for intento in range(1, COM_ID_REINTENTOS + 1):
            if secuencia_com_id["siguiente"] is None and not sincronizar_secuencia():
                return error_propio(
                    502, "COM_ID_NO_SINCRONIZADO",
                    "som-api rechazo la consulta del com_id mas alto; revise la clave SOM_API_KEY",
                )
            siguiente = secuencia_com_id["siguiente"]
            if siguiente > COM_ID_MAXIMO:
                return error_propio(
                    503, "RANGO_COM_ID_AGOTADO",
                    f"Se agoto el rango de com_id del canal CRM ({COM_ID_MINIMO:07d}-{COM_ID_MAXIMO:07d})",
                )

            datos["com_id"] = f"{siguiente:07d}"
            respuesta = llamar_som_o_fallar("POST", "/ordenes", cuerpo=datos)

            if respuesta.status_code == 201:
                secuencia_com_id["siguiente"] = siguiente + 1
                orden = respuesta.json()
                guardar_en_copia_local(orden)
                registrar(
                    "ORDEN_CREADA",
                    f"com_id={orden['com_id']} tipo_orden={orden['tipo_orden']} id={orden['id']}",
                )
                break

            if respuesta.status_code == 409 and codigo_error(respuesta) == "COM_ID_DUPLICADO":
                # Alguien uso ese numero fuera de crm-som: se vuelve a
                # sincronizar con el maximo de som-api y se reintenta.
                registrar("COM_ID_DUPLICADO", f"com_id={datos['com_id']} intento={intento}/{COM_ID_REINTENTOS}")
                secuencia_com_id["siguiente"] = None
                continue

            # Cualquier otro rechazo de som-api (422, 404, 409 de negocio) se
            # devuelve tal cual: el com_id no se consumio.
            break

    return respuesta_desde_som(respuesta)


# --- GET /ordenes -- listar (filtros, orden y paginacion de som-api) --------

@app.route("/ordenes", methods=["GET"])
def listar_ordenes():
    respuesta = llamar_som_o_fallar("GET", "/ordenes", params=parametros_de_consulta())
    if respuesta.status_code == 200:
        for orden in respuesta.json():
            guardar_en_copia_local(orden)
    return respuesta_desde_som(respuesta)


# --- GET /ordenes/<id> -- detalle --------------------------------------------

@app.route("/ordenes/<id_orden>", methods=["GET"])
def obtener_orden(id_orden):
    respuesta = llamar_som_o_fallar("GET", f"/ordenes/{id_orden}", params=parametros_de_consulta())
    if respuesta.status_code == 200:
        guardar_en_copia_local(respuesta.json())
    return respuesta_desde_som(respuesta)


# --- PUT /ordenes/<id> -- reemplazo de prioridad y descripcion ---------------

@app.route("/ordenes/<id_orden>", methods=["PUT"])
def reemplazar_orden(id_orden):
    datos, error = cuerpo_json_o_error()
    if error is not None:
        return error
    respuesta = llamar_som_o_fallar("PUT", f"/ordenes/{id_orden}", cuerpo=datos)
    if respuesta.status_code == 200:
        orden = respuesta.json()
        guardar_en_copia_local(orden)
        registrar("ORDEN_EDITADA", f"com_id={orden['com_id']}")
    return respuesta_desde_som(respuesta)


# --- DELETE /ordenes/<id> -- cancelar -----------------------------------------

@app.route("/ordenes/<id_orden>", methods=["DELETE"])
def cancelar_orden(id_orden):
    respuesta = llamar_som_o_fallar("DELETE", f"/ordenes/{id_orden}")
    if respuesta.status_code == 200:
        orden = respuesta.json()
        guardar_en_copia_local(orden)
        registrar("ORDEN_CANCELADA", f"com_id={orden['com_id']}")
    return respuesta_desde_som(respuesta)


# --- GET /ordenes/<id>/trazabilidad -- historial y trabajo -------------------

@app.route("/ordenes/<id_orden>/trazabilidad", methods=["GET"])
def obtener_trazabilidad(id_orden):
    respuesta = llamar_som_o_fallar("GET", f"/ordenes/{id_orden}/trazabilidad", params=parametros_de_consulta())
    return respuesta_desde_som(respuesta)


# --- GET /suscripciones y GET /ofertas -- datos para el formulario -----------

@app.route("/suscripciones", methods=["GET"])
def listar_suscripciones():
    respuesta = llamar_som_o_fallar("GET", "/suscripciones", params=parametros_de_consulta())
    return respuesta_desde_som(respuesta)


@app.route("/ofertas", methods=["GET"])
def listar_ofertas():
    respuesta = llamar_som_o_fallar("GET", "/ofertas", params=parametros_de_consulta())
    return respuesta_desde_som(respuesta)


# --- GET /eventos -- notificaciones recibidas ---------------------------------

@app.route("/eventos", methods=["GET"])
def listar_eventos():
    return jsonify({"total": eventos_recibidos_total["valor"], "eventos": list(eventos_webhook)}), 200


# --- POST /webhooks/ordenes -- receptor del webhook ---------------------------

@app.route("/webhooks/ordenes", methods=["POST"])
def recibir_webhook():
    """Receptor de las notificaciones de som-api -- Contrato Operativo,
    Seccion 6. Valida el secreto compartido antes de leer el cuerpo."""
    if request.headers.get("X-Webhook-Secret") != WEBHOOK_SECRET_ESPERADO:
        return error_propio(401, "WEBHOOK_SECRET_INVALIDO", "X-Webhook-Secret ausente o incorrecto")

    evento = request.get_json(silent=True)
    if not isinstance(evento, dict):
        return error_propio(400, "JSON_INVALIDO", "El cuerpo de la notificacion debe ser un objeto JSON")

    orden_id = evento.get("orden_id")
    registrar(
        "WEBHOOK_RECIBIDO",
        f"com_id={evento.get('com_id')} tipo_orden={evento.get('tipo_orden')} "
        f"operacion={evento.get('operacion')} "
        f"estado={evento.get('estado_anterior')}->{evento.get('estado_nuevo')} "
        f"canal_origen={evento.get('canal_origen')}",
    )
    eventos_webhook.append({
        "orden_id": orden_id,
        "com_id": evento.get("com_id"),
        "tipo_orden": evento.get("tipo_orden"),
        "subscription_id": evento.get("subscription_id"),
        "operacion": evento.get("operacion"),
        "estado_anterior": evento.get("estado_anterior"),
        "estado_nuevo": evento.get("estado_nuevo"),
        "canal_origen": evento.get("canal_origen"),
        "fecha_evento": evento.get("fecha_evento"),
        "fecha_recepcion": ahora_iso(),
    })
    eventos_recibidos_total["valor"] += 1

    # El payload es liviano por diseno (Contrato Operativo, Seccion 6.5): se
    # confirma el detalle con un GET. Si som-api no responde en este
    # instante, la notificacion igual se reconoce con 200.
    if orden_id:
        try:
            respuesta = llamar_som("GET", f"/ordenes/{orden_id}")
            if respuesta.status_code == 200:
                guardar_en_copia_local(respuesta.json())
        except requests.exceptions.RequestException as excepcion:
            registrar("SOM_API_INALCANZABLE", f"al confirmar la orden {orden_id}: {excepcion}")

    return jsonify({"recibido": True}), 200


# ---------------------------------------------------------------------------
# 8. Mantenimiento periodico: re-registro del webhook y resincronizacion de
#    la copia local. Corre en un hilo propio desde el arranque.
#
#    som-api no persiste el webhook (Contrato Operativo, Seccion 3): si se
#    reinicia, deja de notificar sin avisar. crm-som no tiene forma de
#    consultar si sigue registrado, por lo que lo vuelve a registrar en cada
#    ciclo. Registrar la misma URL otra vez no tiene efectos secundarios en
#    som-api, salvo una linea en su log.
#
#    En el log de crm-som solo se escriben los cambios (registrado, perdido,
#    recuperado), no cada ciclo.
# ---------------------------------------------------------------------------


def registrar_webhook_una_vez():
    """True si som-api acepto el registro."""
    try:
        respuesta = llamar_som("POST", "/webhooks", cuerpo={"url": WEBHOOK_URL_PROPIA})
        if respuesta.status_code == 201:
            if not registro_webhook["registrado"]:
                evento = "WEBHOOK_RECUPERADO" if registro_webhook["ultimo_error"] else "WEBHOOK_REGISTRADO"
                registrar(evento, f"url={WEBHOOK_URL_PROPIA} reregistro cada {WEBHOOK_REREGISTRO_SEGUNDOS} s")
            registro_webhook.update(registrado=True, ultimo_registro=ahora_iso(), ultimo_error=None)
            return True
        detalle = f"som-api respondio {respuesta.status_code} ({codigo_error(respuesta)})"
    except requests.exceptions.RequestException as excepcion:
        detalle = f"som-api inalcanzable: {excepcion.__class__.__name__}"

    if registro_webhook["registrado"] or registro_webhook["ultimo_error"] != detalle:
        registrar("WEBHOOK_NO_REGISTRADO", detalle)
    registro_webhook.update(registrado=False, ultimo_error=detalle)
    return False


def sincronizar_copia_local():
    """Reconstruye la copia local completa desde som-api, pagina a pagina.
    Recupera los cambios cuya notificacion se perdio (por ejemplo, mientras
    som-api estaba reiniciandose y el webhook no estaba registrado)."""
    nueva_copia = {}
    pagina = 1
    while True:
        respuesta = llamar_som(
            "GET", "/ordenes", params={"page": pagina, "size": TAMANO_PAGINA_SINCRONIZACION}
        )
        if respuesta.status_code != 200:
            return
        ordenes = respuesta.json()
        for orden in ordenes:
            nueva_copia[orden["id"]] = orden
        total = int(respuesta.headers.get("X-Total-Count", len(nueva_copia)))
        if not ordenes or len(nueva_copia) >= total:
            break
        pagina += 1
    ordenes_locales.clear()
    ordenes_locales.update(nueva_copia)


def ciclo_mantenimiento():
    while True:
        exito = registrar_webhook_una_vez()
        if exito:
            try:
                sincronizar_copia_local()
            except requests.exceptions.RequestException:
                pass
        time.sleep(WEBHOOK_REREGISTRO_SEGUNDOS if exito else WEBHOOK_REINTENTO_SEGUNDOS)


# ---------------------------------------------------------------------------
# 9. Arranque. threaded=True: crm-som debe poder recibir el webhook entrante
#    mientras tiene una solicitud saliente en curso hacia som-api (Contrato
#    Operativo, Seccion 6.4); sin esto quedarian interbloqueados.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"crm-som v{VERSION} escuchando en el puerto {PORT}", flush=True)
    print(f"Interfaz web:   http://localhost:{PORT}/", flush=True)
    print(f"Estado (JSON):  http://localhost:{PORT}/estado", flush=True)
    print(f"som-api:        {SOM_API_URL}", flush=True)
    print(f"Webhook propio: {WEBHOOK_URL_PROPIA} (re-registro cada {WEBHOOK_REREGISTRO_SEGUNDOS} s)", flush=True)
    print(f"Rango com_id:   {COM_ID_MINIMO:07d}-{COM_ID_MAXIMO:07d}", flush=True)
    print(f"Log de eventos: {LOG_FILE}", flush=True)
    threading.Thread(target=ciclo_mantenimiento, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
