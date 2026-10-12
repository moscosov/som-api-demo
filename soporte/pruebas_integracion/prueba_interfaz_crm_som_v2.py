"""
Prueba de la interfaz web de crm_som.py 2.0 en un navegador real (Chromium
sin pantalla, Playwright), contra som_api_demo.py 2.1.

Uso: python prueba_interfaz_crm_som_v2.py <som_api_demo.py> <crm_som.py> <captura.png>
"""

import os
import subprocess
import sys
import tempfile
import time

import requests
from playwright.sync_api import expect, sync_playwright

SOM_PY, CRM_PY, CAPTURA = sys.argv[1], sys.argv[2], sys.argv[3]
SOM = "http://localhost:8081/api/v2"
CRM = "http://localhost:8082"
GUI = {"X-API-KEY": "DUOC-CUY6142-DEMO"}
trabajo = tempfile.mkdtemp(prefix="crm_ui_")
procesos = []
resultados = []


def verificar(nombre, funcion):
    try:
        funcion()
        resultados.append(True)
        print(f"[OK  ] {nombre}")
    except Exception as excepcion:  # noqa: BLE001 -- se informa cualquier fallo
        resultados.append(False)
        print(f"[FALLA] {nombre} -- {str(excepcion).splitlines()[0][:200]}")


def esperar(url):
    for _ in range(75):
        try:
            requests.get(url, timeout=1)
            return
        except requests.exceptions.RequestException:
            time.sleep(0.2)
    raise RuntimeError(f"no responde {url}")


def lanzar(script, nombre, entorno=None):
    directorio = os.path.join(trabajo, nombre)
    os.makedirs(directorio)
    procesos.append(subprocess.Popen([sys.executable, script], cwd=directorio, env=entorno,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))


def patch_gui(com_id, estado):
    orden = requests.get(f"{SOM}/ordenes", params={"com_id": com_id}, headers=GUI, timeout=3).json()[0]
    requests.patch(f"{SOM}/ordenes/{orden['id']}", json={"estado": estado}, headers=GUI, timeout=3)


try:
    lanzar(SOM_PY, "som")
    esperar(f"{SOM}/openapi.json")
    lanzar(CRM_PY, "crm", dict(os.environ, SOM_API_URL=SOM, WEBHOOK_URL_PROPIA=f"{CRM}/webhooks/ordenes"))
    esperar(f"{CRM}/estado")

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1280, "height": 900})
        errores = []
        # "Failed to load resource" es el aviso de red de un 4xx provocado a
        # proposito (prueba del 422), no un error de JavaScript.
        pagina.on("console", lambda m: errores.append(m.text)
                  if m.type == "error" and "Failed to load resource" not in m.text else None)
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        pagina.on("dialog", lambda d: d.accept())
        pagina.goto(CRM)

        filas = pagina.locator("#tabla-ordenes tbody tr")
        eventos = pagina.locator("#tabla-eventos tbody tr")

        verificar("indicador de webhook en 'registrado'",
                  lambda: expect(pagina.locator("#estado-webhook")).to_have_text("registrado", timeout=8000))
        verificar("formulario ALTA muestra servicio y oferta, oculta suscripcion y puntos", lambda: (
            expect(pagina.locator("#grupo-servicio")).to_be_visible(),
            expect(pagina.locator("#grupo-oferta")).to_be_visible(),
            expect(pagina.locator("#grupo-suscripcion")).to_be_hidden(),
            expect(pagina.locator("#grupo-puntos")).to_be_hidden()))
        verificar("ofertas de INTERNET cargadas desde el catalogo",
                  lambda: expect(pagina.locator("#crear-oferta option")).to_have_count(3))

        def crear_alta():
            pagina.fill("#crear-cliente", "CL-UI")
            pagina.select_option("#crear-oferta", "200102")
            pagina.click("#form-crear button[type=submit]")
            expect(filas.first.locator("td").first).to_have_text("9000001")
            expect(pagina.locator("#resultado-contenido")).to_contain_text("POST /ordenes -> 201")
        verificar("crear ALTA desde el formulario -> com_id 9000001", crear_alta)

        def webhook_actualiza():
            patch_gui("9000001", "EN_PROGRESO")
            patch_gui("9000001", "COMPLETADA")
            expect(eventos).to_have_count(2, timeout=8000)
            expect(eventos.first.locator("td").nth(4)).to_have_text("EN_PROGRESO -> COMPLETADA")
            expect(filas.first.locator("td").nth(6)).to_have_text("COMPLETADA", timeout=8000)
            expect(filas.first.locator("button[data-accion=editar]")).to_be_disabled()
        verificar("webhook aparece solo y la tabla se refresca sin recargar", webhook_actualiza)

        def crear_reloc():
            pagina.select_option("#crear-tipo", "RELOCALIZACION")
            expect(pagina.locator("#grupo-puntos")).to_be_visible()
            expect(pagina.locator("#crear-suscripcion option").first).to_have_attribute("value", "20000001")
            pagina.fill("input[name=actual_x]", "2.5")
            pagina.fill("input[name=actual_y]", "1.75")
            pagina.fill("input[name=actual_ref]", "Living")
            pagina.fill("input[name=destino_x]", "6.125")
            pagina.fill("input[name=destino_y]", "4.5")
            pagina.fill("input[name=destino_ref]", "Dormitorio 2")
            pagina.click("#form-crear button[type=submit]")
            expect(filas.first.locator("td").first).to_have_text("9000002")
            expect(filas.first.locator("td").nth(1)).to_have_text("RELOCALIZACION")
        verificar("crear RELOCALIZACION con suscripcion ACTIVA del cliente", crear_reloc)

        def trazabilidad():
            filas.first.locator("button[data-accion=traza]").click()
            expect(pagina.locator("#trazabilidad")).to_be_visible()
            expect(pagina.locator("#tabla-pasos tbody tr")).to_have_count(4)
            expect(pagina.locator("#tabla-pasos tbody tr").first).to_contain_text("Desconectar el equipo")
            expect(pagina.locator("#traza-resumen")).to_contain_text("6.375 m de cable, 00:37:45")
            pagina.select_option("#traza-idioma", "en")
            expect(pagina.locator("#tabla-pasos tbody tr").first).to_contain_text("Disconnect the device")
        verificar("trazabilidad: 4 pasos, 6,375 m, 00:37:45 y cambio de idioma", trazabilidad)

        def editar():
            filas.first.locator("button[data-accion=editar]").click()
            expect(pagina.locator("#editar")).to_be_visible()
            pagina.select_option("#editar-prioridad", "ALTA")
            pagina.fill("#form-editar input[name=descripcion]", "Traslado <b>urgente</b>")
            pagina.click("#form-editar button[type=submit]")
            expect(pagina.locator("#editar")).to_be_hidden()
            expect(filas.first.locator("td").nth(5)).to_have_text("ALTA")
        verificar("editar prioridad y descripcion (PUT)", editar)

        def cambio_oferta():
            pagina.select_option("#crear-tipo", "CAMBIO_OFERTA")
            expect(pagina.locator("#crear-oferta option").first).to_have_attribute("value", "200101")
            pagina.select_option("#crear-oferta", "200103")
            pagina.click("#form-crear button[type=submit]")
            expect(filas.first.locator("td").first).to_have_text("9000003")
        verificar("CAMBIO_OFERTA con ofertas del servicio de la suscripcion", cambio_oferta)

        def error_visible():
            pagina.select_option("#crear-tipo", "BAJA")
            pagina.fill("#crear-cliente", "SIN-SUSCRIPCIONES")
            pagina.dispatch_event("#crear-cliente", "change")
            expect(pagina.locator("#crear-suscripcion")).to_contain_text("no tiene suscripciones ACTIVA")
            pagina.click("#form-crear button[type=submit]")
            expect(pagina.locator("#resultado-contenido")).to_contain_text("-> 422")
        verificar("cliente sin suscripciones: aviso en el select y 422 visible", error_visible)

        def cancelar():
            fila_reloc = filas.filter(has_text="9000002")
            fila_reloc.locator("button[data-accion=cancelar]").click()
            expect(fila_reloc.locator("td").nth(6)).to_have_text("CANCELADA")
            expect(fila_reloc.locator("button[data-accion=cancelar]")).to_be_disabled()
            expect(fila_reloc.locator("button[data-accion=cancelar]")).to_have_css(
                "background-color", "rgb(184, 192, 202)")
            expect(eventos.first).to_contain_text("DELETE", timeout=8000)
            expect(eventos.first.locator("td").nth(5)).to_have_text("CRM")
        verificar("cancelar (DELETE) con confirmacion y evento de canal CRM", cancelar)

        def paginacion():
            for i in range(9):
                requests.post(f"{CRM}/ordenes", timeout=5, json={
                    "tipo_orden": "ALTA", "cliente_id": f"PG-{i}", "tipo_servicio": "TV", "offer_id": "300101"})
            pagina.click("#btn-buscar")
            expect(pagina.locator("#texto-pagina")).to_have_text("Pagina 1 de 2 - 12 ordenes en total")
            expect(filas).to_have_count(10)
            pagina.click("#btn-siguiente")
            expect(filas).to_have_count(2)
            expect(pagina.locator("#btn-siguiente")).to_be_disabled()
            pagina.click("#btn-anterior")
            pagina.select_option("#filtro-tipo", "RELOCALIZACION")
            pagina.click("#btn-buscar")
            expect(filas).to_have_count(1)
        verificar("paginacion de 10 por pagina y filtro por tipo", paginacion)

        verificar("descripcion con HTML se muestra como texto (sin inyeccion)", lambda: expect(
            pagina.locator("#tabla-ordenes b")).to_have_count(0))

        pagina.select_option("#filtro-tipo", "")
        pagina.fill("#filtro-cliente", "CL-UI")
        pagina.click("#btn-buscar")
        expect(filas).to_have_count(3)
        pagina.select_option("#crear-tipo", "RELOCALIZACION")
        filas.filter(has_text="9000002").locator("button[data-accion=traza]").click()
        pagina.select_option("#traza-idioma", "es")
        time.sleep(1)
        pagina.evaluate("window.scrollTo(0, 0)")
        pagina.screenshot(path=CAPTURA, full_page=True)
        verificar("sin errores de JavaScript en la consola", lambda: (_ for _ in ()).throw(
            AssertionError(errores)) if errores else None)
        navegador.close()
finally:
    for proceso in procesos:
        proceso.terminate()
    print(f"\n{sum(resultados)}/{len(resultados)} pruebas de interfaz OK")
