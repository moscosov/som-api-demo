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
| Versión | 1.1 |
| Fecha | 21/09/2026 |
| Documento asociado | `Contrato_Operativo_OrdenServicio_DuocUC.md` |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 21/09/2026 | Pablo Moscoso | Alineado con Contrato Operativo v1.3. Sección 2: aclarada la existencia de la segunda clave (canal CRM). Sección 4: agregados los comandos `POST /webhooks` y `GET /webhooks/fallos`; notas sobre el campo `notificacion_webhook` en las respuestas de `PATCH` y `DELETE` |

---

## 2. Valores de Sesión

Reemplaza estos valores **una sola vez** — todos los comandos de abajo los usan tal cual.

| Valor | Cómo obtenerlo |
| --- | --- |
| `<HOST>` | Modo demo en vivo: la IP que anuncia el docente al inicio de la sesión. Modo distribuido: `localhost` |
| Clave de acceso | `DUOC-CUY6142-DEMO` — canal GUI, fija, igual en ambos modos (ya viene en el código). Es la clave que usan todos los comandos de esta guía, incluida la transición de estado |

Existe una segunda clave (`DUOC-CUY6142-DEMO-CRM`, canal CRM), reservada para la implementación de referencia del Sistema Cliente (`crm-som`) — no se usa en esta guía (Contrato Operativo, Sección 4).

---

## 3. Flujo Completo

Secuencia copiable de principio a fin: crear una orden, avanzarla y completarla.

```bash
# 1. Crear la orden — copia el "id" de la respuesta, lo necesitas en los pasos siguientes
curl -X POST http://<HOST>:8081/api/v1/ordenes \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"CL-10457","tipo_servicio":"INTERNET","prioridad":"ALTA"}'

# 2. Avanzar a EN_PROGRESO — reemplaza <ID_ORDEN> por el id del paso 1
curl -X PATCH http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"estado":"EN_PROGRESO"}'

# 3. Completar la orden
curl -X PATCH http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"estado":"COMPLETADA"}'
```

---

## 4. Comandos por Operación

### Crear orden

```bash
curl -X POST http://<HOST>:8081/api/v1/ordenes \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"CL-10457","tipo_servicio":"INTERNET","prioridad":"ALTA"}'
```

Respuesta esperada (`201`):

```json
{
  "id": "e0faf7f3-8bb5-4509-87ad-7edd46eac18d",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "prioridad": "ALTA",
  "descripcion": "",
  "estado": "RECIBIDA",
  "fecha_creacion": "2026-09-15T18:32:57Z",
  "fecha_actualizacion": "2026-09-15T18:32:57Z"
}
```

*(`id` y las fechas son distintos en cada ejecución real — copia el `id` para los siguientes comandos.)*

### Listar órdenes

```bash
curl http://<HOST>:8081/api/v1/ordenes \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Respuesta esperada (`200`): lista `[ ... ]` con la representación completa de cada orden creada.

### Consultar una orden

```bash
curl http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Respuesta esperada (`200`): la representación completa de la orden.

### Reemplazar una orden (`PUT`)

```bash
curl -X PUT http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"CL-10457","tipo_servicio":"INTERNET","prioridad":"MEDIA","descripcion":"actualizado"}'
```

Respuesta esperada (`200`): la orden con los campos editables reemplazados (`prioridad` y `descripcion` cambiados en este ejemplo).

### Transicionar estado (`PATCH`)

```bash
curl -X PATCH http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"estado":"EN_PROGRESO"}'
```

Respuesta esperada (`200`): la orden con `"estado": "EN_PROGRESO"`.

*Si hay un webhook registrado (ver más abajo), la respuesta incluye además `"notificacion_webhook": "pendiente"`.*

### Cancelar una orden (`DELETE`)

```bash
curl -X DELETE http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Respuesta esperada (`200`): la orden con `"estado": "CANCELADA"`.

*Si hay un webhook registrado, la respuesta incluye además `"notificacion_webhook": "pendiente"`.*

### Registrar receptor de notificaciones (`POST /webhooks`)

```bash
curl -X POST http://<HOST>:8081/api/v1/webhooks \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://<URL_RECEPTOR>/webhooks/ordenes"}'
```

Respuesta esperada (`201`):

```json
{
  "url": "http://<URL_RECEPTOR>/webhooks/ordenes"
}
```

*Registrar un webhook reemplaza al anterior — solo se admite un receptor activo a la vez (Contrato Operativo, Sección 6.2).*

### Consultar webhooks fallidos (`GET /webhooks/fallos`)

```bash
curl http://<HOST>:8081/api/v1/webhooks/fallos \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Respuesta esperada (`200`): lista `[ ... ]` de intentos de entrega fallidos, vacía si no hay ninguno:

```json
[
  {
    "orden_id": "e0faf7f3-8bb5-4509-87ad-7edd46eac18d",
    "operacion": "PATCH",
    "canal_origen": "GUI",
    "url_destino": "http://<URL_RECEPTOR>/webhooks/ordenes",
    "motivo": "El receptor respondio con codigo 500",
    "fecha_intento": "2026-09-21T14:02:07Z"
  }
]
```

---

## 5. Control de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 21/09/2026 | Pablo Moscoso | Ver Gestión de Versiones, Sección 1 |

---

*Documento de consulta rápida — comando y resultado esperado únicamente. Para entender por qué un comando se comporta así, ver el Diseño Funcional o las Fichas de Contrato asociadas.*
