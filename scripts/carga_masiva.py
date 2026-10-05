import random

import requests

# --- Parte A: datos de conexion -------------------------------------------
SOM_URL = "http://localhost:8081/api/v2"
USUARIO = "gui"
PASSWORD = "Cuy6142!"

# --- Parte B: login para obtener el token -----------------------------------
respuesta = requests.post(SOM_URL + "/loginViaBasic", auth=(USUARIO, PASSWORD))
token = respuesta.json()["token"]
headers = {"X-API-KEY": token}
print("Login correcto. Token obtenido.")

# --- Parte C: catalogo de ofertas agrupado por servicio -------------------
ofertas = requests.get(SOM_URL + "/ofertas", headers=headers).json()
ofertas_por_servicio = {}
for oferta in ofertas:
    servicio = oferta["tipo_servicio"]
    if servicio not in ofertas_por_servicio:
        ofertas_por_servicio[servicio] = []
    ofertas_por_servicio[servicio].append(oferta["offer_id"])
print("Ofertas por servicio:")
for servicio, lista in ofertas_por_servicio.items():
    print(f"  {servicio:<10} {lista}")

# --- Parte D: datos para elegir al azar ------------------------------------
nombres = ["Ana_Rojas", "Luis_Soto", "Carla_Muñoz", "Pedro_Diaz", "Sofia_Vera",
           "Diego_Leon", "Marta_Silva", "Tomas_Reyes", "Paula_Castro", "Jorge_Pinto"]
prioridades = ["ALTA", "MEDIA", "BAJA"]
digitos_verificadores = "0123456789K"

# --- Parte E: crear 50 ordenes ALTA al azar --------------------------------
com_ids_usados = set()
creadas = 0

for numero in range(1, 51):
    com_id = str(random.randint(1000000, 9999999))
    while com_id in com_ids_usados:
        com_id = str(random.randint(1000000, 9999999))
    com_ids_usados.add(com_id)

    servicio = random.choice(list(ofertas_por_servicio.keys()))
    orden = {
        "tipo_orden": "ALTA",
        "com_id": com_id,
        "cliente_id": str(random.randint(10000000, 25999999)) + random.choice(digitos_verificadores),
        "tipo_servicio": servicio,
        "offer_id": random.choice(ofertas_por_servicio[servicio]),
        "prioridad": random.choice(prioridades),
        "descripcion": random.choice(nombres) + ": orden generada por script",
    }

    respuesta = requests.post(SOM_URL + "/ordenes", headers=headers, json=orden)
    if respuesta.status_code == 201:
        creadas = creadas + 1
        print(f"{numero:2d}. Creada  com_id {com_id}  {servicio:<9}  suscripcion {respuesta.json()['subscription_id']}")
    else:
        print(f"{numero:2d}. Error {respuesta.status_code}: {respuesta.json()['error']['mensaje']}")

print(f"\nTotal de ordenes creadas: {creadas} de 50")
