"""
Pruebas de integracion de crm_som.py 2.0 contra som_api_demo.py 2.1.
Levanta ambos servicios como procesos locales en un directorio temporal.

Uso: python prueba_crm_som_v2.py <ruta som_api_demo.py> <ruta crm_som.py>
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

import requests

SOM_PY, CRM_PY = sys.argv[1], sys.argv[2]
PY = sys.executable
SOM = "http://localhost:8081/api/v2"
CRM = "http://localhost:8082"
GUI = {"X-API-KEY": "DUOC-CUY6142-DEMO"}
INTERVALO = 4

trabajo = tempfile.mkdtemp(prefix="crm_v2_")
procesos = {}
resultados = []


def verificar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    estado = "OK  " if condicion else "FALLA"
    print(f"[{estado}] {nombre}" + (f" -- {detalle}" if detalle and not condicion else ""))


def esperar(url, segundos=15):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            requests.get(url, timeout=1)
            return True
        except requests.exceptions.RequestException:
            time.sleep(0.2)
    return False


def iniciar_som():
    directorio = os.path.join(trabajo, "som")
    os.makedirs(directorio, exist_ok=True)
    procesos["som"] = subprocess.Popen(
        [PY, SOM_PY], cwd=directorio, stdout=open(os.path.join(trabajo, "som.out"), "a"),
        stderr=subprocess.STDOUT,
    )
    assert esperar(f"{SOM}/openapi.json"), "som-api no arranco"


def iniciar_crm(extra=None):
    directorio = os.path.join(trabajo, "crm")
    os.makedirs(directorio, exist_ok=True)
    entorno = dict(os.environ, SOM_API_URL=SOM, WEBHOOK_URL_PROPIA=f"{CRM}/webhooks/ordenes",
                   WEBHOOK_REREGISTRO_SEGUNDOS=str(INTERVALO), WEBHOOK_REINTENTO_SEGUNDOS="1")
    entorno.update(extra or {})
    procesos["crm"] = subprocess.Popen(
        [PY, CRM_PY], cwd=directorio, env=entorno, stdout=open(os.path.join(trabajo, "crm.out"), "a"),
        stderr=subprocess.STDOUT,
    )
    assert esperar(f"{CRM}/estado"), "crm-som no arranco"


def detener(nombre):
    procesos[nombre].terminate()
    procesos[nombre].wait(5)


def esperar_condicion(funcion, segundos=10):
    limite = time.time() + segundos
    while time.time() < limite:
        if funcion():
            return True
        time.sleep(0.3)
    return False


def estado_crm():
    return requests.get(f"{CRM}/estado", timeout=3).json()


def eventos():
    return requests.get(f"{CRM}/eventos", timeout=3).json()


def crear(cuerpo):
    return requests.post(f"{CRM}/ordenes", json=cuerpo, timeout=10)


def patch_gui(id_orden, estado_nuevo):
    return requests.patch(f"{SOM}/ordenes/{id_orden}", json={"estado": estado_nuevo}, headers=GUI, timeout=5)


try:
    iniciar_som()
    iniciar_crm()

    # 1. Arranque y registro del webhook
    verificar("webhook registrado al arrancar", esperar_condicion(lambda: estado_crm()["webhook"]["registrado"]))
    e = estado_crm()
    verificar("estado informa version 2.0 y rango", e["version"] == "2.0" and e["com_id"]["rango"] == "9000000-9999999")
    verificar("interfaz web responde HTML", "crm-som v2.0" in requests.get(CRM, timeout=3).text)

    # 2. ALTA con com_id del rango; com_id enviado por el cliente se ignora
    r = crear({"tipo_orden": "ALTA", "com_id": "1234567", "cliente_id": "CL-1", "tipo_servicio": "INTERNET",
               "offer_id": "200102", "prioridad": "ALTA"})
    alta = r.json()
    verificar("ALTA 201 con com_id 9000001", r.status_code == 201 and alta["com_id"] == "9000001", r.text)
    verificar("ALTA genera suscripcion 20000001", alta.get("subscription_id") == "20000001")
    verificar("som-api registra la orden (fuente de verdad)",
              requests.get(f"{SOM}/ordenes/{alta['id']}", headers=GUI, timeout=3).json()["com_id"] == "9000001")

    # 3. Error de validacion no consume com_id
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-1", "tipo_servicio": "INTERNET", "offer_id": "300101"})
    verificar("422 OFERTA_NO_CORRESPONDE_A_SERVICIO llega tal cual", r.status_code == 422
              and r.json()["error"]["codigo"] == "OFERTA_NO_CORRESPONDE_A_SERVICIO", r.text)
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-1", "tipo_servicio": "TV", "offer_id": "300102"})
    alta_tv = r.json()
    verificar("siguiente ALTA usa 9000002 (sin salto por el 422)", alta_tv.get("com_id") == "9000002", r.text)

    # 4. Webhook al transicionar por canal GUI
    patch_gui(alta["id"], "EN_PROGRESO")
    verificar("webhook EN_PROGRESO recibido", esperar_condicion(lambda: eventos()["total"] == 1))
    ev = eventos()["eventos"][-1]
    verificar("evento trae com_id, tipo_orden y subscription_id",
              ev["com_id"] == "9000001" and ev["tipo_orden"] == "ALTA" and ev["subscription_id"] == "20000001"
              and ev["canal_origen"] == "GUI", ev)
    patch_gui(alta["id"], "COMPLETADA")
    verificar("webhook COMPLETADA recibido", esperar_condicion(lambda: eventos()["total"] == 2))
    r = requests.get(f"{CRM}/suscripciones", params={"cliente_id": "CL-1", "estado": "ACTIVA"}, timeout=3)
    verificar("suscripcion ACTIVA tras completar el ALTA (proxy /suscripciones)",
              r.status_code == 200 and [s["subscription_id"] for s in r.json()] == ["20000001"]
              and r.headers.get("X-Total-Count") == "1", r.text)

    # 5. RELOCALIZACION y trazabilidad (valores del Contrato de Datos 6.5/6.6)
    r = crear({"tipo_orden": "RELOCALIZACION", "cliente_id": "CL-1", "subscription_id": "20000001",
               "punto_actual": {"x": 2.5, "y": 1.75, "referencia": "Living"},
               "punto_destino": {"x": 6.125, "y": 4.5, "referencia": "Dormitorio 2"}})
    reloc = r.json()
    verificar("RELOCALIZACION 201, 6.375 m y 2265000 ms", r.status_code == 201 and reloc["distancia_m"] == 6.375
              and reloc["duracion_estimada_ms"] == 2265000 and reloc["com_id"] == "9000003", r.text)
    r = requests.get(f"{CRM}/ordenes/{reloc['id']}/trazabilidad", params={"idioma": "es"}, timeout=3)
    t = r.json()
    verificar("trazabilidad en espanol con 4 pasos", r.status_code == 200 and len(t["trabajo"]["pasos"]) == 4
              and t["trabajo"]["pasos"][0]["texto"] == "Desconectar el equipo en el punto actual (Living)", r.text)

    # 6. PUT solo prioridad y descripcion
    r = requests.put(f"{CRM}/ordenes/{reloc['id']}", json={"prioridad": "BAJA", "descripcion": "Traslado"}, timeout=5)
    verificar("PUT 200", r.status_code == 200 and r.json()["prioridad"] == "BAJA", r.text)
    r = requests.put(f"{CRM}/ordenes/{reloc['id']}", json={"prioridad": "BAJA", "descripcion": "x",
                                                            "cliente_id": "OTRO"}, timeout=5)
    verificar("PUT con inmutable distinto -> 409 CAMPO_INMUTABLE", r.status_code == 409
              and r.json()["error"]["codigo"] == "CAMPO_INMUTABLE", r.text)

    # 7. DELETE por canal CRM dispara webhook con canal CRM
    total = eventos()["total"]
    r = requests.delete(f"{CRM}/ordenes/{reloc['id']}", timeout=5)
    verificar("DELETE 200 con notificacion_webhook pendiente", r.status_code == 200
              and r.json().get("notificacion_webhook") == "pendiente", r.text)
    verificar("webhook de la cancelacion con canal CRM",
              esperar_condicion(lambda: eventos()["total"] == total + 1)
              and eventos()["eventos"][-1]["canal_origen"] == "CRM")

    # 8. CAMBIO_OFERTA y BAJA
    r = crear({"tipo_orden": "CAMBIO_OFERTA", "cliente_id": "CL-1", "subscription_id": "20000001",
               "offer_id": "200103"})
    verificar("CAMBIO_OFERTA 201", r.status_code == 201 and r.json()["com_id"] == "9000004", r.text)
    r = crear({"tipo_orden": "CAMBIO_OFERTA", "cliente_id": "CL-1", "subscription_id": "20000001",
               "offer_id": "200102"})
    verificar("CAMBIO_OFERTA a la oferta vigente -> 409 OFERTA_SIN_CAMBIO", r.status_code == 409
              and r.json()["error"]["codigo"] == "OFERTA_SIN_CAMBIO", r.text)
    r = crear({"tipo_orden": "BAJA", "cliente_id": "CL-1", "subscription_id": "20000001"})
    verificar("BAJA 201 con com_id 9000005", r.status_code == 201 and r.json()["com_id"] == "9000005", r.text)

    # 9. Colision: alguien usa a mano el proximo numero del rango
    requests.post(f"{SOM}/ordenes", headers=GUI, timeout=5, json={
        "tipo_orden": "ALTA", "com_id": "9000006", "cliente_id": "CL-2", "tipo_servicio": "TV", "offer_id": "300101"})
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-3", "tipo_servicio": "TELEFONIA", "offer_id": "400101"})
    verificar("colision 9000006 -> reintento con 9000007", r.status_code == 201 and r.json()["com_id"] == "9000007",
              r.text)

    # 10. com_id de estudiantes (fuera del rango) no afecta la secuencia
    requests.post(f"{SOM}/ordenes", headers=GUI, timeout=5, json={
        "tipo_orden": "ALTA", "com_id": "0000005", "cliente_id": "12345678", "tipo_servicio": "INTERNET",
        "offer_id": "200101"})
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-3", "tipo_servicio": "TV", "offer_id": "300101"})
    verificar("orden de estudiante 0000005 no altera la secuencia", r.json().get("com_id") == "9000008", r.text)

    # 11. Listado: filtros, paginacion y X-Total-Count
    r = requests.get(f"{CRM}/ordenes", params=[("size", "2"), ("page", "2"), ("sortBy", "com_id")], timeout=3)
    verificar("paginacion size=2 page=2 y X-Total-Count", r.status_code == 200 and len(r.json()) == 2
              and r.headers.get("X-Total-Count") == "9", f"{r.status_code} {r.headers.get('X-Total-Count')}")
    r = requests.get(f"{CRM}/ordenes", params=[("estado", "RECIBIDA"), ("estado", "CANCELADA")], timeout=3)
    verificar("filtro multivalor estado", r.status_code == 200
              and {o["estado"] for o in r.json()} <= {"RECIBIDA", "CANCELADA"} and len(r.json()) >= 2)
    r = requests.get(f"{CRM}/ordenes", params={"size": "500"}, timeout=3)
    verificar("parametro invalido -> 400 PARAMETRO_INVALIDO de som-api", r.status_code == 400
              and r.json()["error"]["codigo"] == "PARAMETRO_INVALIDO", r.text)
    r = requests.get(f"{CRM}/ofertas", params={"q": "fibra", "limit": "1"}, timeout=3)
    verificar("proxy /ofertas con q y limit", r.status_code == 200 and len(r.json()) == 1)
    r = requests.get(f"{CRM}/ordenes/00000000-0000-0000-0000-000000000000", timeout=3)
    verificar("orden inexistente -> 404 ORDEN_NO_ENCONTRADA", r.status_code == 404
              and r.json()["error"]["codigo"] == "ORDEN_NO_ENCONTRADA")

    # 12. Errores propios de crm-som
    r = requests.post(f"{CRM}/ordenes", data="no-json", headers={"Content-Type": "text/plain"}, timeout=3)
    verificar("cuerpo no JSON -> 400 JSON_INVALIDO", r.status_code == 400
              and r.json()["error"]["codigo"] == "JSON_INVALIDO")
    r = requests.post(f"{CRM}/webhooks/ordenes", json={"orden_id": "x"}, headers={"X-Webhook-Secret": "malo"},
                      timeout=3)
    verificar("webhook con secreto incorrecto -> 401", r.status_code == 401
              and r.json()["error"]["codigo"] == "WEBHOOK_SECRET_INVALIDO")

    # 13. Reinicio de som-api: se pierde el webhook y crm-som lo recupera
    detener("som")
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-4", "tipo_servicio": "TV", "offer_id": "300101"})
    verificar("som-api caido -> 502 SOM_API_INALCANZABLE", r.status_code == 502
              and r.json()["error"]["codigo"] == "SOM_API_INALCANZABLE", r.text)
    verificar("crm-som detecta que el webhook no esta registrado",
              esperar_condicion(lambda: not estado_crm()["webhook"]["registrado"], INTERVALO + 3))
    iniciar_som()
    verificar("crm-som re-registra el webhook tras el reinicio",
              esperar_condicion(lambda: estado_crm()["webhook"]["registrado"], 8))
    total = eventos()["total"]
    lista = requests.get(f"{SOM}/ordenes", params={"com_id": "9000008"}, headers=GUI, timeout=3).json()
    patch_gui(lista[0]["id"], "EN_PROGRESO")
    verificar("datos persistidos y webhook entregado tras reinicio de som-api",
              esperar_condicion(lambda: eventos()["total"] == total + 1))

    # 14. Reinicio rapido de som-api (sin que crm-som lo note): recuperacion en un ciclo
    detener("som")
    iniciar_som()
    total = eventos()["total"]
    patch_gui(lista[0]["id"], "COMPLETADA")
    time.sleep(1.5)
    perdido = eventos()["total"] == total
    verificar("reinicio rapido: el evento inmediato se pierde (comportamiento esperado)", perdido)
    verificar("copia local resincronizada en el siguiente ciclo", esperar_condicion(
        lambda: estado_crm()["webhook"]["registrado"], INTERVALO + 3))
    time.sleep(INTERVALO + 1)
    estados = requests.get(f"{SOM}/ordenes", params={"com_id": "9000008"}, headers=GUI, timeout=3).json()
    verificar("orden 9000008 COMPLETADA en som-api", estados[0]["estado"] == "COMPLETADA")

    # 15. Reinicio de crm-som: la secuencia continua desde som-api
    detener("crm")
    iniciar_crm()
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-5", "tipo_servicio": "INTERNET", "offer_id": "200101"})
    verificar("tras reiniciar crm-som continua con 9000009", r.json().get("com_id") == "9000009", r.text)

    # 16. Concurrencia: 10 creaciones simultaneas, todas con com_id distinto
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(10) as ejecutor:
        respuestas = list(ejecutor.map(lambda i: crear({"tipo_orden": "ALTA", "cliente_id": f"CC-{i}",
                                                       "tipo_servicio": "TV", "offer_id": "300101"}), range(10)))
    com_ids = [r.json().get("com_id") for r in respuestas]
    verificar("10 creaciones simultaneas: 201 y com_id unicos y consecutivos",
              all(r.status_code == 201 for r in respuestas)
              and sorted(com_ids) == [f"{9000010 + i:07d}" for i in range(10)], com_ids)

    # 17. Rango agotado
    requests.post(f"{SOM}/ordenes", headers=GUI, timeout=5, json={
        "tipo_orden": "ALTA", "com_id": "9999999", "cliente_id": "CL-9", "tipo_servicio": "TV", "offer_id": "300101"})
    detener("crm")
    iniciar_crm()
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-5", "tipo_servicio": "INTERNET", "offer_id": "200101"})
    verificar("rango agotado -> 503 RANGO_COM_ID_AGOTADO", r.status_code == 503
              and r.json()["error"]["codigo"] == "RANGO_COM_ID_AGOTADO", r.text)

    # 18. Clave incorrecta
    detener("crm")
    iniciar_crm({"SOM_API_KEY": "CLAVE-MALA"})
    time.sleep(1.5)
    e = estado_crm()
    verificar("clave incorrecta: webhook no registrado con 401 informado", not e["webhook"]["registrado"]
              and "401" in (e["webhook"]["ultimo_error"] or ""), e)
    r = crear({"tipo_orden": "ALTA", "cliente_id": "CL-5", "tipo_servicio": "INTERNET", "offer_id": "200101"})
    verificar("clave incorrecta: creacion -> 502 COM_ID_NO_SINCRONIZADO", r.status_code == 502
              and r.json()["error"]["codigo"] == "COM_ID_NO_SINCRONIZADO", r.text)

finally:
    for proceso in procesos.values():
        if proceso.poll() is None:
            proceso.terminate()
    total_ok = sum(1 for _, ok in resultados if ok)
    print(f"\n{total_ok}/{len(resultados)} pruebas OK -- registros en {trabajo}")
    if os.environ.get("BORRAR_TRABAJO") == "1":
        shutil.rmtree(trabajo, ignore_errors=True)
