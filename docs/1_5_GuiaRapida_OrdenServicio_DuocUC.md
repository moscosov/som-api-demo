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
| Versión | 1.0 |
| Fecha | 15/09/2026 |
| Documento asociado | `Contrato_Operativo_OrdenServicio_DuocUC.md` |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |

---

## 2. Valores de Sesión

Reemplaza estos valores **una sola vez** — todos los comandos de abajo los usan tal cual.

| Valor | Cómo obtenerlo |
| --- | --- |
| `<HOST>` | Modo demo en vivo: la IP que anuncia el docente al inicio de la sesión. Modo distribuido: `localhost` |
| Clave de acceso | `DUOC-CUY6142-DEMO` — fija, igual en ambos modos (ya viene en el código; no es un valor que debas completar) |

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

### Cancelar una orden (`DELETE`)

```bash
curl -X DELETE http://<HOST>:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Respuesta esperada (`200`): la orden con `"estado": "CANCELADA"`.

---

## 5. Control de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |

---

*Documento de consulta rápida — comando y resultado esperado únicamente. Para entender por qué un comando se comporta así, ver el Diseño Funcional o las Fichas de Contrato asociadas.*
