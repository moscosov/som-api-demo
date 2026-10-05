"""Prueba integral de som_api_demo.py v2 contra un servidor real."""
import base64, json, os, random, shutil, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

PORT = 18081
BASE = f"http://127.0.0.1:{PORT}/api/v2"
DIR = tempfile.mkdtemp(prefix="somv2_")
DATA = os.path.join(DIR, "data", "som_data.json")
fallas = []
total = 0


def check(cond, nombre, detalle=""):
    global total
    total += 1
    if not cond:
        fallas.append(f"{nombre} {detalle}")
        print("  FALLA:", nombre, detalle)


def iniciar():
    env = dict(os.environ, PORT=str(PORT), SOM_DATA_FILE=DATA)
    p = subprocess.Popen([sys.executable, os.path.abspath("som_api_demo.py")], cwd=DIR, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        try:
            requests.get(f"{BASE}/openapi.json", timeout=0.5)
            return p
        except requests.ConnectionError:
            time.sleep(0.2)
    print(p.stdout.read()); raise SystemExit("no arranca")


def detener(p):
    p.terminate(); p.wait(5)


def login(u="gui", pw="Cuy6142!"):
    return requests.post(f"{BASE}/loginViaBasic", auth=(u, pw))


def code(r):
    try:
        return r.json()["error"]["codigo"]
    except Exception:
        return None


# Receptor de webhook
recibidos = []
class Receptor(BaseHTTPRequestHandler):
    def do_POST(self):
        largo = int(self.headers["Content-Length"])
        recibidos.append((self.headers.get("X-Webhook-Secret"), json.loads(self.rfile.read(largo))))
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
receptor = HTTPServer(("127.0.0.1", 18099), Receptor)
threading.Thread(target=receptor.serve_forever, daemon=True).start()

srv = iniciar()
try:
    # --- Login y autenticacion
    r = login(); check(r.status_code == 200, "login 200")
    tok = r.json()["token"]
    check(tok.startswith("gui|") and len(tok.split("|")[1]) == 43, "formato token", tok)
    check(login().json()["token"] != tok, "token distinto por login")
    r = login("gui", "mala"); check(r.status_code == 401 and code(r) == "CREDENCIALES_INVALIDAS"
                                    and "Basic" in r.headers.get("WWW-Authenticate", ""), "login malo 401")
    r = requests.post(f"{BASE}/loginViaBasic"); check(r.status_code == 401, "login sin auth 401")
    h = {"Authorization": "basic " + base64.b64encode(b"crm:Cuy6142!").decode()}
    r = requests.post(f"{BASE}/loginViaBasic", headers=h); check(r.status_code == 200 and r.json()["token"].startswith("crm|"), "basic minuscula")
    H = {"X-API-KEY": tok}
    r = requests.get(f"{BASE}/ofertas"); check(r.status_code == 401 and code(r) == "NO_AUTORIZADO", "sin credencial 401")
    r = requests.get(f"{BASE}/ofertas", headers={"X-API-KEY": "x"}); check(r.status_code == 401, "credencial mala 401")
    r = requests.get(f"{BASE}/ofertas", params={"key": tok}); check(r.status_code == 200, "key en URL con token")
    r = requests.get(f"{BASE}/ofertas", headers={"x-api-key": "DUOC-CUY6142-DEMO-CRM"}); check(r.status_code == 200, "clave fija canal, header minusculas")
    r = requests.get(f"{BASE}/ofertas", headers={"X-API-KEY": tok}, params={"key": "mala"}); check(r.status_code == 200, "header tiene precedencia")

    # --- Docs
    r = requests.get(f"{BASE}/docs"); check(r.status_code == 200 and "swagger-ui" in r.text, "docs")
    r = requests.get(f"{BASE}/openapi.json"); check(r.status_code == 200 and r.json()["openapi"].startswith("3.0"), "openapi")

    # --- Ofertas
    r = requests.get(f"{BASE}/ofertas", headers=H, params={"q": "FIBRA", "limit": 1})
    check(r.json() == [{"offer_id": "200101", "nombre": "Fibra 300 Mbps", "tipo_servicio": "INTERNET"}], "ofertas q limit", r.text)
    r = requests.get(f"{BASE}/ofertas", headers=H, params={"tipo_servicio": "TV"}); check(len(r.json()) == 3, "ofertas tv")
    r = requests.get(f"{BASE}/ofertas", headers=H, params={"limit": 0}); check(r.status_code == 400 and code(r) == "PARAMETRO_INVALIDO", "limit 0")
    r = requests.get(f"{BASE}/ofertas/999999", headers=H); check(r.status_code == 404 and code(r) == "OFERTA_NO_ENCONTRADA", "oferta 404")
    r = requests.get(f"{BASE}/ofertas/300102", headers=H); check(r.json()["nombre"] == "TV Premium", "oferta detalle")

    def post(body):
        return requests.post(f"{BASE}/ordenes", headers=H, json=body)

    def patch(i, body):
        return requests.patch(f"{BASE}/ordenes/{i}", headers=H, json=body)

    CL = "CL-10457"
    # --- Formato y schema
    r = requests.post(f"{BASE}/ordenes", headers=H, data='{"a":'); check(r.status_code == 400 and code(r) == "JSON_INVALIDO", "json invalido")
    r = requests.post(f"{BASE}/ordenes", headers=H, data='{}'); check(r.status_code == 400, "sin content-type 400")
    r = post({"tipo_orden": "TRASLADO", "com_id": "1000001"}); check(r.status_code == 422 and "tipo_orden" in r.json()["error"]["mensaje"], "RV-01")
    r = post({"cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200102"}); check(r.status_code == 422 and code(r) == "SCHEMA_INVALIDO", "RV-02 sin com_id", r.text)
    r = post({"com_id": 1000001, "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200102"}); check(r.status_code == 422, "RV-03 com_id entero")
    r = post({"com_id": "100001", "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200102"}); check(r.status_code == 422, "RV-03 6 digitos")
    r = post({"com_id": "1000001", "cliente_id": "", "tipo_servicio": "INTERNET", "offer_id": "200102"}); check(r.status_code == 422, "RV-04")
    r = post({"com_id": "1000001", "cliente_id": CL, "tipo_servicio": "FAX", "offer_id": "200102"}); check(r.status_code == 422, "RV-05")
    r = post({"com_id": "1000001", "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "299999"}); check(r.status_code == 404 and code(r) == "OFERTA_NO_ENCONTRADA", "RN-02")
    r = post({"com_id": "1000001", "cliente_id": CL, "tipo_servicio": "TV", "offer_id": "200102"}); check(r.status_code == 422 and code(r) == "OFERTA_NO_CORRESPONDE_A_SERVICIO", "RN-03")

    # --- ALTA (ignora campos no aplicables y de solo lectura)
    r = post({"tipo_orden": "ALTA", "com_id": "1000001", "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200102",
              "prioridad": "ALTA", "descripcion": "Alta de Fibra 600 Mbps residencial", "estado": "COMPLETADA",
              "subscription_id": "abc", "id": "x", "punto_actual": {"x": 1}})
    check(r.status_code == 201, "ALTA 201", r.text)
    alta = r.json()
    check(list(alta.keys()) == ["id", "tipo_orden", "com_id", "cliente_id", "tipo_servicio", "offer_id", "subscription_id",
                                "punto_actual", "punto_destino", "distancia_m", "duracion_estimada_ms", "prioridad",
                                "descripcion", "estado", "fecha_creacion", "fecha_actualizacion"], "orden de campos")
    check(alta["subscription_id"] == "20000001" and alta["estado"] == "RECIBIDA" and alta["id"] != "x"
          and alta["punto_actual"] is None, "ALTA valores", alta)
    S1 = alta["subscription_id"]
    r = requests.get(f"{BASE}/suscripciones/{S1}", headers=H); check(r.json()["estado"] == "PENDIENTE", "sub PENDIENTE")
    r = post({"com_id": "1000001", "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200101"}); check(r.status_code == 409 and code(r) == "COM_ID_DUPLICADO", "RN-01")
    r = post({"com_id": "1000099", "cliente_id": CL, "tipo_servicio": "TV", "offer_id": "300101"}); check(r.json()["subscription_id"] == "30000001", "correlativo por servicio")

    reloc = {"tipo_orden": "RELOCALIZACION", "com_id": "1000002", "cliente_id": CL, "subscription_id": S1,
             "punto_actual": {"x": 2.5, "y": 1.75, "referencia": "Living"},
             "punto_destino": {"x": 6.125, "y": 4.5, "referencia": "Dormitorio 2"}, "descripcion": "Traslado del router al dormitorio"}
    r = post(reloc); check(r.status_code == 409 and code(r) == "SUSCRIPCION_NO_ACTIVA", "RN-07 sub PENDIENTE")
    r = post({**reloc, "punto_destino": {"x": 2.50, "y": 1.75}}); check(r.status_code == 422 and code(r) == "PUNTOS_IDENTICOS", "RN-09")
    r = requests.post(f"{BASE}/ordenes", headers={**H, "Content-Type": "application/json"},
                      data=json.dumps(reloc).replace('"x": 6.125', '"x": NaN')); check(r.status_code == 422, "NaN rechazado", r.text)
    r = post({**reloc, "punto_actual": {"x": 101, "y": 1}}); check(r.status_code == 422, "RV-06 rango")
    r = post({**reloc, "subscription_id": "20999999"}); check(r.status_code == 404 and code(r) == "SUSCRIPCION_NO_ENCONTRADA", "RN-04")

    check(patch(alta["id"], {"estado": "EN_PROGRESO"}).status_code == 200, "ALTA EN_PROGRESO")
    r = patch(alta["id"], {"estado": "COMPLETADA"}); check(r.status_code == 200, "ALTA COMPLETADA")
    r = requests.get(f"{BASE}/suscripciones/{S1}", headers=H); check(r.json()["estado"] == "ACTIVA", "sub ACTIVA")
    r = post({**reloc, "cliente_id": "OTRO"}); check(r.status_code == 409 and code(r) == "SUSCRIPCION_NO_PERTENECE_A_CLIENTE", "RN-05")
    r = post({**reloc, "tipo_servicio": "TV"}); check(r.status_code == 422 and code(r) == "SERVICIO_NO_CORRESPONDE_A_SUSCRIPCION", "RN-06")

    # --- RELOCALIZACION y calculo
    r = post(reloc); check(r.status_code == 201, "RELOC 201", r.text)
    R = r.json()
    check(R["distancia_m"] == 6.375 and R["duracion_estimada_ms"] == 2265000 and R["tipo_servicio"] == "INTERNET"
          and R["offer_id"] is None, "calculo reloc", R)
    t = requests.get(f"{BASE}/ordenes/{R['id']}/trazabilidad", headers=H, params={"idioma": "es"}).json()
    esperado = [
        {"secuencia": 1, "texto": "Desconectar el equipo en el punto actual (Living)", "distancia_m": 0, "duracion_ms": 600000},
        {"secuencia": 2, "texto": "Tender cable hacia el este", "distancia_m": 3.625, "duracion_ms": 435000},
        {"secuencia": 3, "texto": "Tender cable hacia el norte", "distancia_m": 2.75, "duracion_ms": 330000},
        {"secuencia": 4, "texto": "Conectar y verificar el equipo en el punto de destino (Dormitorio 2)", "distancia_m": 0, "duracion_ms": 900000}]
    check(t["trabajo"]["pasos"] == esperado and t["idioma"] == "es", "pasos es", t)
    t = requests.get(f"{BASE}/ordenes/{R['id']}/trazabilidad", headers=H).json()
    check(t["idioma"] == "en" and t["trabajo"]["pasos"][1]["texto"] == "Run cable to the east", "idioma default en")
    r = requests.get(f"{BASE}/ordenes/{R['id']}/trazabilidad", headers=H, params={"idioma": "fr"}); check(r.status_code == 400, "idioma invalido 400")
    t = requests.get(f"{BASE}/ordenes/{alta['id']}/trazabilidad", headers=H).json()
    check(t["trabajo"] is None and [e["estado"] for e in t["historial"]] == ["RECIBIDA", "EN_PROGRESO", "COMPLETADA"], "trazab ALTA")
    # tramo cero se omite, direccion oeste/sur, sin referencia
    r = post({**reloc, "com_id": "1000050", "punto_actual": {"x": 5, "y": 3}, "punto_destino": {"x": 5, "y": 1.1}})
    t = requests.get(f"{BASE}/ordenes/{r.json()['id']}/trazabilidad", headers=H, params={"idioma": "es"}).json()
    check([p["texto"] for p in t["trabajo"]["pasos"]] == ["Desconectar el equipo en el punto actual", "Tender cable hacia el sur",
          "Conectar y verificar el equipo en el punto de destino"] and t["trabajo"]["distancia_m"] == 1.9
          and t["trabajo"]["pasos"][1]["duracion_ms"] == 228000, "tramo cero omitido", t)
    check(requests.delete(f"{BASE}/ordenes/{r.json()['id']}", headers=H).status_code == 200, "cancelar reloc auxiliar")

    # --- Webhook + flujo opcion B
    check(requests.post(f"{BASE}/webhooks", headers=H, json={"url": "http://127.0.0.1:18099/hook"}).status_code == 201, "webhook registro")
    check(requests.post(f"{BASE}/webhooks", headers=H, json={"url": ""}).status_code == 422, "webhook url vacia")
    B = post({"tipo_orden": "BAJA", "com_id": "1000004", "cliente_id": CL, "subscription_id": S1}).json()
    check(B["estado"] == "RECIBIDA", "BAJA encolada")
    r = patch(R["id"], {"estado": "EN_PROGRESO"}); check(r.status_code == 200 and r.json().get("notificacion_webhook") == "pendiente", "R EN_PROGRESO")
    r = patch(B["id"], {"estado": "EN_PROGRESO"}); check(r.status_code == 409 and code(r) == "ORDEN_EN_CURSO", "RN-10")
    n = len(recibidos)
    r = patch(R["id"], {"descripcion": "solo texto"}); check(r.status_code == 200 and "notificacion_webhook" not in r.json(), "PATCH descripcion sin webhook")
    r = patch(R["id"], {"estado": "COMPLETADA", "descripcion": "x"}); check(r.status_code == 200, "R COMPLETADA")
    time.sleep(0.5)
    check(len(recibidos) == n + 1, "un solo webhook por cambio de estado", len(recibidos) - n)
    sec, pay = recibidos[-1]
    check(sec == "DUOC-CUY6142-DEMO-WEBHOOK-SECRET" and pay["tipo_orden"] == "RELOCALIZACION" and pay["com_id"] == "1000002"
          and pay["subscription_id"] == S1 and pay["estado_nuevo"] == "COMPLETADA" and pay["canal_origen"] == "GUI"
          and pay["operacion"] == "PATCH", "payload webhook", pay)
    check(patch(B["id"], {"estado": "EN_PROGRESO"}).status_code == 200, "B EN_PROGRESO")
    check(patch(B["id"], {"estado": "COMPLETADA"}).status_code == 200, "B COMPLETADA")
    check(requests.get(f"{BASE}/suscripciones/{S1}", headers=H).json()["estado"] == "BAJA", "sub BAJA")
    r = post({"tipo_orden": "CAMBIO_OFERTA", "com_id": "1000005", "cliente_id": CL, "subscription_id": S1, "offer_id": "200103"})
    check(r.status_code == 409 and code(r) == "SUSCRIPCION_NO_ACTIVA", "CAMBIO sobre BAJA")

    # --- Cola: CAMBIO en RECIBIDA invalidado por BAJA completada; RN-08 reevaluada
    def alta_activa(com, offer="200101"):
        a = post({"com_id": com, "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": offer}).json()
        patch(a["id"], {"estado": "EN_PROGRESO"}); patch(a["id"], {"estado": "COMPLETADA"})
        return a["subscription_id"]
    S2 = alta_activa("2000001")
    r = post({"tipo_orden": "CAMBIO_OFERTA", "com_id": "2000002", "cliente_id": CL, "subscription_id": S2, "offer_id": "200101"})
    check(r.status_code == 409 and code(r) == "OFERTA_SIN_CAMBIO", "RN-08 creacion")
    r = post({"tipo_orden": "CAMBIO_OFERTA", "com_id": "2000002", "cliente_id": CL, "subscription_id": S2, "offer_id": "300101"})
    check(r.status_code == 422 and code(r) == "OFERTA_NO_CORRESPONDE_A_SERVICIO", "RN-03 cambio")
    C1 = post({"tipo_orden": "CAMBIO_OFERTA", "com_id": "2000003", "cliente_id": CL, "subscription_id": S2, "offer_id": "200103"}).json()
    C2 = post({"tipo_orden": "CAMBIO_OFERTA", "com_id": "2000004", "cliente_id": CL, "subscription_id": S2, "offer_id": "200103"}).json()
    patch(C1["id"], {"estado": "EN_PROGRESO"}); patch(C1["id"], {"estado": "COMPLETADA"})
    check(requests.get(f"{BASE}/suscripciones/{S2}", headers=H).json()["offer_id"] == "200103", "efecto CAMBIO_OFERTA")
    r = patch(C2["id"], {"estado": "EN_PROGRESO", "descripcion": "no debe quedar"})
    check(r.status_code == 409 and code(r) == "OFERTA_SIN_CAMBIO", "RN-08 reevaluada")
    check(requests.get(f"{BASE}/ordenes/{C2['id']}", headers=H).json()["descripcion"] == "", "PATCH atomico")
    BA = post({"tipo_orden": "BAJA", "com_id": "2000005", "cliente_id": CL, "subscription_id": S2}).json()
    RE = post({**reloc, "com_id": "2000006", "subscription_id": S2}).json()
    patch(BA["id"], {"estado": "EN_PROGRESO"}); patch(BA["id"], {"estado": "COMPLETADA"})
    r = patch(RE["id"], {"estado": "EN_PROGRESO"}); check(r.status_code == 409 and code(r) == "SUSCRIPCION_NO_ACTIVA", "RN-07 reevaluada")
    check(requests.delete(f"{BASE}/ordenes/{RE['id']}", headers=H).status_code == 200, "cancelar orden huerfana")

    # --- PUT / PATCH / DELETE
    S3 = alta_activa("3000001")
    O = post({**reloc, "com_id": "3000002", "subscription_id": S3}).json()
    r = requests.put(f"{BASE}/ordenes/{O['id']}", headers=H, json={"prioridad": "ALTA"}); check(r.status_code == 422, "RV-07")
    r = requests.put(f"{BASE}/ordenes/{O['id']}", headers=H, json={"prioridad": "ALTA", "descripcion": "d", "cliente_id": "OTRO"})
    check(r.status_code == 409 and code(r) == "CAMPO_INMUTABLE", "RN-13")
    r = requests.put(f"{BASE}/ordenes/{O['id']}", headers=H, json={**O, "prioridad": "BAJA", "descripcion": "nuevo", "estado": "COMPLETADA"})
    check(r.status_code == 200 and r.json()["prioridad"] == "BAJA" and r.json()["estado"] == "RECIBIDA", "PUT con inmutables iguales", r.text)
    check(patch(O["id"], {}).status_code == 422, "PATCH vacio")
    check(patch(O["id"], {"prioridad": "ALTA"}).status_code == 422, "PATCH campo no permitido")
    check(patch(O["id"], {"estado": "COMPLETADA"}).json()["error"]["codigo"] == "TRANSICION_INVALIDA", "RN-11")
    r = requests.delete(f"{BASE}/ordenes/{O['id']}", headers=H); check(r.status_code == 200 and r.json()["estado"] == "CANCELADA", "DELETE")
    r = requests.delete(f"{BASE}/ordenes/{O['id']}", headers=H); check(r.status_code == 409 and code(r) == "ORDEN_EN_ESTADO_TERMINAL", "DELETE terminal")
    r = patch(O["id"], {"descripcion": "x"}); check(r.status_code == 409 and code(r) == "ORDEN_EN_ESTADO_TERMINAL", "PATCH terminal")
    r = requests.put(f"{BASE}/ordenes/{O['id']}", headers=H, json={"prioridad": "ALTA", "descripcion": "d"}); check(code(r) == "ORDEN_EN_ESTADO_TERMINAL", "PUT terminal")
    A4 = post({"com_id": "4000001", "cliente_id": CL, "tipo_servicio": "TELEFONIA", "offer_id": "400101"}).json()
    requests.delete(f"{BASE}/ordenes/{A4['id']}", headers=H)
    check(requests.get(f"{BASE}/suscripciones/{A4['subscription_id']}", headers=H).json()["estado"] == "ANULADA", "sub ANULADA")
    check(requests.get(f"{BASE}/ordenes/noexiste", headers=H).status_code == 404, "orden 404")
    check(patch("noexiste", {"x": 1}).status_code == 404, "PATCH 404 antes que schema")
    check(requests.get(f"{BASE}/ordenes/{O['id']}", headers=H, params={"includeOferta": "si"}).status_code == 400, "includeOferta invalido")

    # --- 50 altas aleatorias, listado, paginacion, orden
    servicios = {"INTERNET": ["200101", "200102", "200103"], "TV": ["300101", "300102", "300103"], "TELEFONIA": ["400101", "400102", "400103"]}
    usados = set()
    for _ in range(50):
        com = str(random.randint(5000000, 9999999))
        while com in usados:
            com = str(random.randint(5000000, 9999999))
        usados.add(com)
        s = random.choice(list(servicios))
        r = post({"com_id": com, "cliente_id": str(random.randint(10000000, 25000000)), "tipo_servicio": s,
                  "offer_id": random.choice(servicios[s])})
        check(r.status_code == 201, "alta aleatoria", r.text)
    r = requests.get(f"{BASE}/ordenes", headers=H)
    totalo = int(r.headers["X-Total-Count"]); check(len(r.json()) == 20 and totalo >= 60, "pagina 1", totalo)
    todas = []
    pagina = 1
    while len(todas) < totalo:
        todas += requests.get(f"{BASE}/ordenes", headers=H, params={"page": pagina, "size": 25}).json(); pagina += 1
    check(len(todas) == totalo and len({o["id"] for o in todas}) == totalo, "recorrido de paginas")
    check([o["fecha_creacion"] for o in todas] == sorted(o["fecha_creacion"] for o in todas), "orden default creacion")
    r = requests.get(f"{BASE}/ordenes", headers=H, params={"sortBy": "subscription_id", "includeOferta": "true", "size": 100})
    subs = [o["subscription_id"] for o in r.json()]
    check(subs == sorted(subs) and all("oferta" in o for o in r.json()), "sortBy + includeOferta")
    alta1 = [o for o in r.json() if o["com_id"] == "1000001"][0]
    check(alta1["oferta"]["nombre"] == "Fibra 600 Mbps", "oferta expandida")
    r = requests.get(f"{BASE}/ordenes", headers=H, params={"sortBy": "com_id", "order": "desc", "size": 100})
    coms = [o["com_id"] for o in r.json()]; check(coms == sorted(coms, reverse=True), "order desc")
    r = requests.get(f"{BASE}/ordenes", headers=H, params=[("estado", "RECIBIDA"), ("estado", "EN_PROGRESO"), ("size", 100)])
    check(all(o["estado"] in ("RECIBIDA", "EN_PROGRESO") for o in r.json()) and int(r.headers["X-Total-Count"]) >= 50, "multivalor")
    for p, v in (("sortBy", "precio"), ("size", "101"), ("page", "0"), ("estado", "ABIERTA"), ("order", "up")):
        r = requests.get(f"{BASE}/ordenes", headers=H, params={p: v}); check(r.status_code == 400 and code(r) == "PARAMETRO_INVALIDO", f"param {p}")
    r = requests.get(f"{BASE}/ordenes", headers=H, params={"page": 99}); check(r.json() == [], "pagina fuera de rango")
    r = requests.get(f"{BASE}/suscripciones", headers=H, params={"cliente_id": CL, "estado": "ACTIVA"})
    check([s["subscription_id"] for s in r.json()] == [S3] and r.headers["X-Total-Count"] == "1", "suscripciones filtro", r.text)

    # --- Concurrencia
    with ThreadPoolExecutor(20) as ex:
        res = list(ex.map(lambda _: post({"com_id": "4444444", "cliente_id": CL, "tipo_servicio": "TV", "offer_id": "300101"}).status_code, range(20)))
    check(res.count(201) == 1 and res.count(409) == 19, "com_id concurrente", res)
    S5 = alta_activa("5000000x"[:7])
    X1 = post({**reloc, "com_id": "4000011", "subscription_id": S5}).json()
    X2 = post({"tipo_orden": "BAJA", "com_id": "4000012", "cliente_id": CL, "subscription_id": S5}).json()
    with ThreadPoolExecutor(2) as ex:
        res = sorted(ex.map(lambda i: patch(i, {"estado": "EN_PROGRESO"}).status_code, [X1["id"], X2["id"]]))
    check(res == [200, 409], "RN-10 concurrente", res)

    # --- Webhook caido
    receptor.shutdown(); receptor.server_close()
    patch(X1["id"], {"estado": "CANCELADA"}) if res else None
    time.sleep(4)
    f = requests.get(f"{BASE}/webhooks/fallos", headers=H).json()
    check(len(f) >= 1, "fallo webhook registrado", f)

    conteo_ordenes = int(requests.get(f"{BASE}/ordenes", headers=H).headers["X-Total-Count"])
finally:
    detener(srv)

# --- Persistencia y reinicio
with open(DATA) as fh:
    datos = json.load(fh)
check(len(datos["ordenes"]) == conteo_ordenes and "historial" in next(iter(datos["ordenes"].values())), "archivo persistido")
srv = iniciar()
try:
    r = requests.get(f"{BASE}/ofertas", headers=H); check(r.status_code == 401, "token perdido al reiniciar")
    H2 = {"X-API-KEY": login().json()["token"]}
    r = requests.get(f"{BASE}/ordenes", headers=H2); check(int(r.headers["X-Total-Count"]) == conteo_ordenes, "ordenes tras reinicio")
    corr = datos["correlativos"]["INTERNET"]
    r = requests.post(f"{BASE}/ordenes", headers=H2, json={"com_id": "8888888", "cliente_id": CL, "tipo_servicio": "INTERNET", "offer_id": "200101"})
    check(r.json()["subscription_id"] == f"20{corr + 1:06d}", "correlativo continua", r.json()["subscription_id"])
finally:
    detener(srv)

# --- Archivo corrupto
with open(DATA, "w") as fh:
    fh.write("{corrupto")
env = dict(os.environ, PORT=str(PORT), SOM_DATA_FILE=DATA)
p = subprocess.run([sys.executable, os.path.abspath("som_api_demo.py")], cwd=DIR, env=env, capture_output=True, text=True, timeout=20)
check(p.returncode != 0 and "no se puede cargar" in (p.stderr + p.stdout), "corrupto no arranca", p.stderr[-200:])
with open(DATA) as fh:
    check(fh.read() == "{corrupto", "corrupto no sobrescrito")

shutil.rmtree(DIR)
print(f"\n{total - len(fallas)}/{total} verificaciones OK")
if fallas:
    print("FALLAS:", *fallas, sep="\n - ")
    sys.exit(1)
