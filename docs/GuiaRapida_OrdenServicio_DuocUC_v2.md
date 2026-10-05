<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">Guía Rápida — Orden de Servicio</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Guía Rápida — Orden de Servicio (API Demo eTOM/SOM) |
| Versión | 2.0 |
| Fecha | 05/10/2026 |
| Documento asociado | `Contrato_Operativo_OrdenServicio_DuocUC.md` (2.0) |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 21/09/2026 | Pablo Moscoso | Alineado con Contrato Operativo v1.3. Sección 2: aclarada la existencia de la segunda clave (canal CRM). Sección 4: agregados los comandos `POST /webhooks` y `GET /webhooks/fallos`; notas sobre el campo `notificacion_webhook` en las respuestas de `PATCH` y `DELETE` |
| 2.0 | 05/10/2026 | Pablo Moscoso | Alineado con Contrato Operativo 2.0 (ruta base `/api/v2`). Sección 2: login con usuario y contraseña, token de sesión y variables de shell. Sección 3: flujo de alta y relocalización. Sección 4: comandos de login, ofertas, los cuatro tipos de orden, listado con filtros y paginación, actualización parcial, trazabilidad, suscripciones y documentación navegable. Respuestas esperadas obtenidas de una ejecución real del servicio 2.0 |

---

## 2. Valores de Sesión

Los comandos están escritos para una terminal `bash` (sesión SSH en la instancia, Linux o macOS). Se definen **una sola vez** tres valores; todos los comandos de las Secciones 3 y 4 los usan tal cual.

| Variable | Valor |
| --- | --- |
| `SOM` | `http://<HOST>:8081/api/v2`. `<HOST>` es la IP pública de la instancia AWS, `localhost` dentro de la propia instancia, o la IP que anuncia el docente en una demostración |
| Usuario y contraseña | `gui` / `Cuy6142!` |
| `TOKEN` | El valor de `token` que devuelve el login. Se pierde al reiniciar el servicio: si un comando responde `401`, repetir el login |

```bash
SOM=http://<HOST>:8081/api/v2

curl -X POST "$SOM/loginViaBasic" -u 'gui:Cuy6142!'
```

```json
{"token":"gui|yOg3m_KYoyozii1mDyDcCztyrkUJj0P1uCkQqSA3oco"}
```

Copiar el token completo, incluido `gui|`, **entre comillas simples**:

```bash
TOKEN='gui|yOg3m_KYoyozii1mDyDcCztyrkUJj0P1uCkQqSA3oco'
```

Los identificadores que devuelve el servicio (`id` de cada orden) se guardan del mismo modo en una variable (`ID_ALTA`, `ID_RELOC`, `ID_ORDEN`) cuando un comando lo indica.

`curl` muestra cada respuesta en una sola línea. En esta guía se muestran formateadas; `id` y fechas cambian en cada ejecución.

---

## 3. Flujo Completo

Contratar un servicio, completarlo, relocalizar el punto de red y consultar los pasos de trabajo.

```bash
# 1. Buscar la oferta
curl "$SOM/ofertas?q=fibra" -H "X-API-KEY: $TOKEN"

# 2. Crear el ALTA. Copiar el "id" de la respuesta en ID_ALTA y anotar el "subscription_id"
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"ALTA","com_id":"1000001","cliente_id":"CL-10457","tipo_servicio":"INTERNET","offer_id":"200102"}'
ID_ALTA='<ID_DEL_PASO_2>'

# 3. Ejecutar y completar el ALTA
curl -X PATCH "$SOM/ordenes/$ID_ALTA" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' -d '{"estado":"EN_PROGRESO"}'
curl -X PATCH "$SOM/ordenes/$ID_ALTA" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' -d '{"estado":"COMPLETADA"}'

# 4. Crear la RELOCALIZACION sobre la suscripcion del paso 2. Copiar su "id" en ID_RELOC
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"RELOCALIZACION","com_id":"1000002","cliente_id":"CL-10457","subscription_id":"20000001","punto_actual":{"x":2.5,"y":1.75,"referencia":"Living"},"punto_destino":{"x":6.125,"y":4.5,"referencia":"Dormitorio 2"}}'
ID_RELOC='<ID_DEL_PASO_4>'

# 5. Consultar los pasos de trabajo en espanol
curl "$SOM/ordenes/$ID_RELOC/trazabilidad?idioma=es" -H "X-API-KEY: $TOKEN"

# 6. Ejecutar y completar la RELOCALIZACION
curl -X PATCH "$SOM/ordenes/$ID_RELOC" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' -d '{"estado":"EN_PROGRESO"}'
curl -X PATCH "$SOM/ordenes/$ID_RELOC" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' -d '{"estado":"COMPLETADA"}'
```

---

## 4. Comandos por Operación

### Login (`POST /loginViaBasic`)

Ver Sección 2. Respuesta esperada (`200`): `{"token":"gui|..."}`.

### Buscar ofertas (`GET /ofertas`)

```bash
curl "$SOM/ofertas?q=fibra&limit=1" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`):

```json
[
  {"offer_id": "200101", "nombre": "Fibra 300 Mbps", "tipo_servicio": "INTERNET"}
]
```

Misma consulta con la credencial en la URL, filtrando por servicio:

```bash
curl "$SOM/ofertas?tipo_servicio=TV&key=$TOKEN"
```

Respuesta esperada (`200`): las tres ofertas de `TV` (`300101`, `300102`, `300103`).

### Consultar una oferta (`GET /ofertas/{offer_id}`)

```bash
curl "$SOM/ofertas/200102" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`):

```json
{"offer_id": "200102", "nombre": "Fibra 600 Mbps", "tipo_servicio": "INTERNET"}
```

### Crear un `ALTA` (`POST /ordenes`)

```bash
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"ALTA","com_id":"1000001","cliente_id":"CL-10457","tipo_servicio":"INTERNET","offer_id":"200102","descripcion":"Alta de Fibra 600 Mbps residencial"}'
```

Respuesta esperada (`201`):

```json
{
  "id": "04059e8b-fab1-402a-aa63-b6beb941bab4",
  "tipo_orden": "ALTA",
  "com_id": "1000001",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "offer_id": "200102",
  "subscription_id": "20000001",
  "punto_actual": null,
  "punto_destino": null,
  "distancia_m": null,
  "duracion_estimada_ms": null,
  "prioridad": "MEDIA",
  "descripcion": "Alta de Fibra 600 Mbps residencial",
  "estado": "RECIBIDA",
  "fecha_creacion": "2026-10-05T11:13:03Z",
  "fecha_actualizacion": "2026-10-05T11:13:03Z"
}
```

### Crear una `RELOCALIZACION` (`POST /ordenes`)

Requiere que el `ALTA` de la suscripción esté `COMPLETADA`.

```bash
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"RELOCALIZACION","com_id":"1000002","cliente_id":"CL-10457","subscription_id":"20000001","punto_actual":{"x":2.5,"y":1.75,"referencia":"Living"},"punto_destino":{"x":6.125,"y":4.5,"referencia":"Dormitorio 2"},"descripcion":"Traslado del router al dormitorio"}'
```

Respuesta esperada (`201`), campos propios de la relocalización:

```json
{
  "id": "77fe0be2-3dcb-4458-b48c-5ff5504df36c",
  "tipo_orden": "RELOCALIZACION",
  "com_id": "1000002",
  "tipo_servicio": "INTERNET",
  "offer_id": null,
  "subscription_id": "20000001",
  "punto_actual": {"x": 2.5, "y": 1.75, "referencia": "Living"},
  "punto_destino": {"x": 6.125, "y": 4.5, "referencia": "Dormitorio 2"},
  "distancia_m": 6.375,
  "duracion_estimada_ms": 2265000,
  "estado": "RECIBIDA"
}
```

### Crear un `CAMBIO_OFERTA` (`POST /ordenes`)

```bash
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"CAMBIO_OFERTA","com_id":"1000003","cliente_id":"CL-10457","subscription_id":"20000001","offer_id":"200103"}'
```

Respuesta esperada (`201`): la orden con `"tipo_orden": "CAMBIO_OFERTA"`, `"offer_id": "200103"` y `"estado": "RECIBIDA"`.

### Crear una `BAJA` (`POST /ordenes`)

```bash
curl -X POST "$SOM/ordenes" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"BAJA","com_id":"1000004","cliente_id":"CL-10457","subscription_id":"20000001"}'
```

Respuesta esperada (`201`): la orden con `"tipo_orden": "BAJA"`, `"offer_id": null` y `"estado": "RECIBIDA"`.

### Listar órdenes (`GET /ordenes`)

```bash
curl -i "$SOM/ordenes?sortBy=com_id&includeOferta=true&page=1&size=2" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): los headers (`-i`) incluyen el total de órdenes, y el cuerpo, una página de dos órdenes ordenadas por `com_id`, cada una con el campo `oferta`:

```
HTTP/1.1 200 OK
Content-Type: application/json
X-Total-Count: 4
```

```json
[
  {"id": "04059e8b-...", "com_id": "1000001", "tipo_orden": "ALTA", "estado": "COMPLETADA",
   "oferta": {"offer_id": "200102", "nombre": "Fibra 600 Mbps", "tipo_servicio": "INTERNET"}},
  {"id": "77fe0be2-...", "com_id": "1000002", "tipo_orden": "RELOCALIZACION", "estado": "RECIBIDA",
   "oferta": null}
]
```

*(Cuerpo abreviado: cada orden viene con su representación completa.)*

### Listar órdenes pendientes de ejecución (`GET /ordenes`, filtro multivalor)

```bash
curl -i "$SOM/ordenes?estado=RECIBIDA&estado=EN_PROGRESO" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): las órdenes en `RECIBIDA` o `EN_PROGRESO`, con su total en `X-Total-Count`.

### Consultar una orden (`GET /ordenes/{id}`)

```bash
ID_ORDEN='<ID_DE_LA_ORDEN>'
curl "$SOM/ordenes/$ID_ORDEN?includeOferta=true" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): la representación completa de la orden, con el campo `oferta` al final.

### Avanzar el estado (`PATCH /ordenes/{id}`)

```bash
curl -X PATCH "$SOM/ordenes/$ID_ORDEN" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"estado":"EN_PROGRESO"}'
```

Respuesta esperada (`200`): la orden con `"estado": "EN_PROGRESO"`. Repetir con `{"estado":"COMPLETADA"}` para completarla.

*Si hay un webhook registrado, la respuesta incluye además `"notificacion_webhook": "pendiente"`.*

### Actualizar solo la descripción (`PATCH /ordenes/{id}`)

```bash
curl -X PATCH "$SOM/ordenes/$ID_ORDEN" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"descripcion":"Cliente solicita visita en horario AM"}'
```

Respuesta esperada (`200`): la orden con la nueva `descripcion` y el mismo `estado`.

### Reemplazar los campos editables (`PUT /ordenes/{id}`)

```bash
curl -X PUT "$SOM/ordenes/$ID_ORDEN" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prioridad":"ALTA","descripcion":"Cliente solicita visita en horario AM"}'
```

Respuesta esperada (`200`): la orden con `"prioridad": "ALTA"` y la `descripcion` enviada.

### Cancelar una orden (`DELETE /ordenes/{id}`)

```bash
curl -X DELETE "$SOM/ordenes/$ID_ORDEN" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): la orden con `"estado": "CANCELADA"`.

*Si hay un webhook registrado, la respuesta incluye además `"notificacion_webhook": "pendiente"`.*

### Consultar la trazabilidad (`GET /ordenes/{id}/trazabilidad`)

```bash
curl "$SOM/ordenes/$ID_RELOC/trazabilidad?idioma=es" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`):

```json
{
  "orden_id": "77fe0be2-3dcb-4458-b48c-5ff5504df36c",
  "com_id": "1000002",
  "tipo_orden": "RELOCALIZACION",
  "subscription_id": "20000001",
  "idioma": "es",
  "historial": [
    {"estado": "RECIBIDA", "fecha": "2026-10-05T11:13:03Z"}
  ],
  "trabajo": {
    "distancia_m": 6.375,
    "duracion_estimada_ms": 2265000,
    "pasos": [
      {"secuencia": 1, "texto": "Desconectar el equipo en el punto actual (Living)", "distancia_m": 0, "duracion_ms": 600000},
      {"secuencia": 2, "texto": "Tender cable hacia el este", "distancia_m": 3.625, "duracion_ms": 435000},
      {"secuencia": 3, "texto": "Tender cable hacia el norte", "distancia_m": 2.75, "duracion_ms": 330000},
      {"secuencia": 4, "texto": "Conectar y verificar el equipo en el punto de destino (Dormitorio 2)", "distancia_m": 0, "duracion_ms": 900000}
    ]
  }
}
```

Sin `?idioma=es`, los textos de los pasos vienen en inglés. En una orden que no es `RELOCALIZACION`, `trabajo` es `null`.

### Listar suscripciones (`GET /suscripciones`)

```bash
curl -i "$SOM/suscripciones?cliente_id=CL-10457&estado=ACTIVA" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`), con `X-Total-Count: 1` en los headers:

```json
[
  {
    "subscription_id": "20000001",
    "cliente_id": "CL-10457",
    "tipo_servicio": "INTERNET",
    "offer_id": "200102",
    "estado": "ACTIVA",
    "orden_alta_id": "04059e8b-fab1-402a-aa63-b6beb941bab4",
    "fecha_creacion": "2026-10-05T11:13:03Z",
    "fecha_actualizacion": "2026-10-05T11:13:03Z"
  }
]
```

### Consultar una suscripción (`GET /suscripciones/{subscription_id}`)

```bash
curl "$SOM/suscripciones/20000001" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): la suscripción, con la misma forma que cada elemento del listado.

### Registrar receptor de notificaciones (`POST /webhooks`)

```bash
curl -X POST "$SOM/webhooks" -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"url":"http://<URL_RECEPTOR>/webhooks/ordenes"}'
```

Respuesta esperada (`201`):

```json
{"url": "http://<URL_RECEPTOR>/webhooks/ordenes"}
```

*`<URL_RECEPTOR>` es el host y puerto del receptor (por ejemplo, `crm-som:8082` dentro de la red Docker). Registrar un webhook reemplaza al anterior.*

### Consultar webhooks fallidos (`GET /webhooks/fallos`)

```bash
curl "$SOM/webhooks/fallos" -H "X-API-KEY: $TOKEN"
```

Respuesta esperada (`200`): lista de intentos de entrega fallidos, vacía si no hay ninguno:

```json
[
  {
    "orden_id": "fa964666-8580-4ef6-ae0b-950a3b4e29a1",
    "operacion": "DELETE",
    "canal_origen": "GUI",
    "url_destino": "http://localhost:8099/webhooks/ordenes",
    "motivo": "HTTPConnectionPool(host='localhost', port=8099): ... Connection refused",
    "fecha_intento": "2026-10-05T11:13:03Z"
  }
]
```

### Documentación navegable (`GET /docs` y `GET /openapi.json`)

Abrir en el navegador, sin credencial:

```
http://<HOST>:8081/api/v2/docs
```

Respuesta esperada: la página Swagger UI con todos los endpoints. La especificación en JSON está en `http://<HOST>:8081/api/v2/openapi.json`.

---

## 5. Control de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 21/09/2026 | Pablo Moscoso | Ver Gestión de Versiones, Sección 1 |
| 2.0 | 05/10/2026 | Pablo Moscoso | Ver Gestión de Versiones, Sección 1 |

---

*Documento de consulta rápida — comando y resultado esperado únicamente. Para entender por qué un comando se comporta así, ver el Diseño Funcional o las Fichas de Contrato asociadas.*
