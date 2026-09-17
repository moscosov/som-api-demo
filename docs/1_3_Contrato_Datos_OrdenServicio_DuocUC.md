<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">Contrato de Datos — Orden de Servicio</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Contrato de Datos — Orden de Servicio (API Demo eTOM/SOM) |
| Versión | 1.2 |
| Fecha | 14/09/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | EA2 — Fundamentos y Consumo de APIs (complementa 2.3/2.4) |
| Documento asociado | Contrato Operativo y de Protocolo — Orden de Servicio |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 14/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 14/09/2026 | Pablo Moscoso | Validación de conformidad contra `Estandar_Documentacion_API_CUY6142.md` (Sección 3, checklist de Ficha de Contrato) — sin cambios de contenido |
| 1.2 | 14/09/2026 | Pablo Moscoso | Sección 4 generalizada: la obligatoriedad de `cliente_id`/`tipo_servicio` y la regla de solo-lectura ahora cubren también el reemplazo completo vía `PUT`, agregado al Contrato Operativo y de Protocolo |

---

## 2. Propósito y Alcance

Este documento define el **Contrato de Datos** (schema) del recurso `Orden de Servicio`, expuesto por el API demo del curso. El Contrato de Datos especifica qué forma debe tener una representación válida del recurso — con independencia del lenguaje o framework en que esté implementado el servicio. El comportamiento de red, protocolo, autenticación y códigos de estado HTTP se documenta por separado en el **Contrato Operativo y de Protocolo**.

Este API es una simplificación pedagógica del proceso eTOM **Order Handling** (Process Identifier 1.1.1.5, dentro de Customer Relationship Management / Operations), responsable de aceptar y emitir órdenes, con seguimiento de estado y notificación de finalización al cliente. Se inspira en el tipo de recurso que gestiona un sistema real de Service Order Management (SOM) como el operado en Claro Ecuador, y se alinea conceptualmente — sin pretender conformidad ni certificación — con el API abierto de TM Forum **TMF641 (Service Ordering Management)**.

No cubre otros procesos eTOM (Assurance, Billing) ni la totalidad de Order Handling — se limita a un único recurso con ciclo de vida simplificado, suficiente para ilustrar los conceptos de contrato de datos, validación de schema y máquina de estados.

---

## 3. Definición del Recurso: Orden de Servicio

| Campo | Tipo | Obligatoriedad | Origen | Descripción |
| --- | --- | --- | --- | --- |
| `id` | string (UUID) | Generado por servidor | Servidor | Identificador único de la orden. Solo lectura. |
| `cliente_id` | string | Obligatorio en creación | Cliente | Identificador del cliente solicitante. |
| `tipo_servicio` | enum | Obligatorio en creación | Cliente | Ver valores permitidos abajo. |
| `prioridad` | enum | Opcional | Cliente | Ver valores permitidos abajo. Default: `MEDIA`. |
| `descripcion` | string | Opcional | Cliente | Detalle libre de la solicitud. |
| `estado` | enum | Generado/controlado por servidor | Servidor | Ver máquina de estados (Sección 5). Solo lectura para el cliente. |
| `fecha_creacion` | string (ISO 8601) | Generado por servidor | Servidor | Solo lectura. |
| `fecha_actualizacion` | string (ISO 8601) | Generado por servidor | Servidor | Solo lectura. Se actualiza en cada transición de `estado`. |

### Valores permitidos

| Campo | Valores |
| --- | --- |
| `tipo_servicio` | `INTERNET`, `TELEFONIA`, `TV` |
| `prioridad` | `ALTA`, `MEDIA`, `BAJA` |
| `estado` | `RECIBIDA`, `EN_PROGRESO`, `COMPLETADA`, `CANCELADA` |

---

## 4. Reglas de Validación del Contrato

- `cliente_id` y `tipo_servicio` son obligatorios en toda solicitud que envíe una representación completa del recurso — creación (`POST`) o reemplazo completo (`PUT`, ver Contrato Operativo y de Protocolo). Su ausencia constituye una violación del Contrato de Datos.
- `tipo_servicio` y `prioridad` deben pertenecer exactamente a los valores permitidos listados en la Sección 3. Cualquier otro valor constituye una violación del contrato, no un error de protocolo.
- `id`, `estado`, `fecha_creacion` y `fecha_actualizacion` son campos de solo lectura: si el cliente los incluye en una solicitud de creación o de reemplazo (`PUT`), el servidor los ignora y mantiene o genera sus propios valores — en particular, `PUT` nunca modifica `estado`; solo `PATCH` puede transicionarlo (Sección 5). No es un error — es responsabilidad del servidor, no del cliente.
- Un campo obligatorio ausente, o un valor fuera del dominio permitido, se comunica al cliente según el código de estado definido en el Contrato Operativo y de Protocolo (Sección 7 de ese documento) — no se define aquí, para mantener la separación entre "qué es válido" (este documento) y "cómo se comunica un fallo" (documento operativo).

---

## 5. Máquina de Estados de `estado`

```
RECIBIDA ──► EN_PROGRESO ──► COMPLETADA
    │              │
    └──────────────┴──► CANCELADA
```

Transiciones válidas:

| Desde | Hacia | Válida |
| --- | --- | --- |
| RECIBIDA | EN_PROGRESO | Sí |
| EN_PROGRESO | COMPLETADA | Sí |
| RECIBIDA | CANCELADA | Sí |
| EN_PROGRESO | CANCELADA | Sí |
| COMPLETADA | cualquiera | No |
| CANCELADA | cualquiera | No |

Una transición no listada aquí es válida como dato (es un valor de `estado` permitido por el schema) pero inválida como **regla de negocio**. Esta distinción es intencional: separa la validación de schema (Contrato de Datos) de la validación de reglas de negocio (documentada como código `409` en el Contrato Operativo y de Protocolo).

---

## 6. Ejemplos de Representación del Recurso

**Cuerpo de solicitud de creación (`POST`)** — solo campos que el cliente puede enviar:

```json
{
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "prioridad": "ALTA",
  "descripcion": "Activación de plan residencial 200 Mbps"
}
```

**Representación completa del recurso** (lo que devuelve el servidor tras la creación):

```json
{
  "id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "prioridad": "ALTA",
  "descripcion": "Activación de plan residencial 200 Mbps",
  "estado": "RECIBIDA",
  "fecha_creacion": "2026-09-14T15:32:10Z",
  "fecha_actualizacion": "2026-09-14T15:32:10Z"
}
```

---

## 7. Política de Versionado del Contrato

- Agregar un campo **opcional** nuevo: cambio menor, no rompe clientes existentes.
- Eliminar un campo, renombrarlo, o cambiar su tipo/obligatoriedad: cambio mayor, rompe clientes existentes — requiere nueva versión del contrato y coordinación con el Contrato Operativo (que referencia la versión en la base URL, ej. `/api/v1`).
- Esta ficha documenta la versión **1.0** del contrato.

---

## 8. Glosario

| Término | Definición |
| --- | --- |
| Contrato de Datos (Data Contract) | Especificación formal de la estructura, tipos y reglas de validación de un recurso, independiente de su implementación. |
| Schema | Sinónimo técnico de Contrato de Datos en el contexto de APIs; también usado para referirse a su representación formal (ej. JSON Schema). |
| Campo de solo lectura | Campo cuyo valor es generado y controlado por el servidor; el cliente no puede establecerlo ni modificarlo. |
| Enum | Conjunto cerrado y finito de valores permitidos para un campo. |
| Contrato Operativo | Documento complementario que define protocolo, transporte, autenticación y códigos de estado — ver ficha asociada. |

---

*Documento de referencia — no es un procedimiento (MOP). Se actualiza únicamente cuando cambia la definición del recurso.*
