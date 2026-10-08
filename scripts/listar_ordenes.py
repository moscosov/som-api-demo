import requests

# --- Parte A: datos de conexion y login ------------------------------------
SOM_URL = "http://localhost:8081/api/v2"
respuesta = requests.post(SOM_URL + "/loginViaBasic", auth=("gui", "Cuy6142!"))
headers = {"X-API-KEY": respuesta.json()["token"]}

# --- Parte B: recorrer todas las paginas -----------------------------------
todas = []
pagina = 1
while True:
    parametros = {"sortBy": "cliente_id", "page": pagina, "size": 20}
    respuesta = requests.get(SOM_URL + "/ordenes", headers=headers, params=parametros)
    lote = respuesta.json()
    total = int(respuesta.headers["X-Total-Count"])
    todas = todas + lote
    print(f"Pagina {pagina}: {len(lote)} ordenes recibidas ({len(todas)} de {total})")
    if len(todas) >= total or len(lote) == 0:
        break
    pagina = pagina + 1

# --- Parte C: mostrar la lista completa ------------------------------------
print()
print(f"{'N':>3}  {'COM_ID':<8} {'CLIENTE':<11} {'SERVICIO':<10} {'SUSCRIPCION':<12} {'ESTADO':<12}")
for numero, orden in enumerate(todas, start=1):
    print(f"{numero:>3}  {orden['com_id']:<8} {orden['cliente_id']:<11} {orden['tipo_servicio']:<10} "
          f"{orden['subscription_id']:<12} {orden['estado']:<12}")

# --- Parte D: resumen por servicio -----------------------------------------
conteo = {}
for orden in todas:
    servicio = orden["tipo_servicio"]
    conteo[servicio] = conteo.get(servicio, 0) + 1

print()
print("Resumen por servicio:")
for servicio, cantidad in conteo.items():
    print(f"  {servicio:<10} {cantidad}")
print(f"Total de ordenes: {len(todas)}")
