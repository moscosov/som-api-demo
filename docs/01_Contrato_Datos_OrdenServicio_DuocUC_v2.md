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
| Versión | 2.0 |
| Fecha | 05/10/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | EA2 — Fundamentos y Consumo de APIs (2.3 / 2.4); base de la actividad formativa 2.4.2 |
| Documento asociado | Contrato Operativo y de Protocolo — Orden de Servicio (versión 2.0) |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 14/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 14/09/2026 | Pablo Moscoso | Validación de conformidad contra `Estandar_Documentacion_API_CUY6142.md` (Sección 3, checklist de Ficha de Contrato) — sin cambios de contenido |
| 1.2 | 14/09/2026 | Pablo Moscoso | Sección 4 generalizada: la obligatoriedad de `cliente_id`/`tipo_servicio` y la regla de solo-lectura ahora cubren también el reemplazo completo, agregado al Contrato Operativo y de Protocolo |
| 2.0 | 05/10/2026 | Pablo Moscoso | Cambio mayor. Sección 2: alcance ampliado a tipos de orden, suscripciones y catálogo de ofertas. Sección 3: campos `tipo_orden`, `com_id`, `offer_id`, `subscription_id`, `punto_actual`, `punto_destino`, `distancia_m`, `duracion_estimada_ms`; estructura Punto; recursos asociados Suscripción y Oferta; representación de Trazabilidad. Sección 4: reglas identificadas (RV, RN), campos inmutables y editables, cálculo de relocalización. Sección 5: máquina de estados de la suscripción, efectos de las órdenes sobre la suscripción y serialización de la ejecución. Sección 7: corregida (indicaba versión 1.0) y justificación del cambio mayor |

---

## 2. Propósito y Alcance

Este documento define el **Contrato de Datos** (schema) del recurso `Orden de Servicio` y de los recursos asociados que la orden necesita para tener sentido de negocio: `Suscripción`, `Oferta` y la representación de `Trazabilidad` de una orden. El Contrato de Datos especifica qué forma debe tener una representación válida de cada recurso y qué reglas de negocio la gobiernan, con independencia del lenguaje o framework en que esté implementado el servicio. El comportamiento de red, protocolo, autenticación, rutas, parámetros de consulta y códigos de estado HTTP se documenta por separado en el **Contrato Operativo y de Protocolo**.

Este API es una simplificación pedagógica del proceso eTOM **Order Handling** (Process Identifier 1.1.1.5, dentro de Customer Relationship Management / Operations), responsable de aceptar y emitir órdenes, con seguimiento de estado y notificación de finalización al cliente. Se inspira en el tipo de recurso que gestiona un sistema real de Service Order Management (SOM) como el operado en Claro Ecuador, y se alinea conceptualmente — sin pretender conformidad ni certificación — con los siguientes APIs abiertos de TM Forum:

| Elemento de este contrato | Referencia conceptual TM Forum |
| --- | --- |
| Orden de Servicio y `tipo_orden` | TMF641 Service Ordering Management (acciones `add`, `modify`, `delete` de un ítem de orden) |
| Suscripción | TMF638 Service Inventory Management (instancia de servicio activa de un cliente) |
| Oferta | TMF620 Product Catalog Management (oferta comercial de catálogo) |

Correspondencia de los tipos de orden con las acciones de TMF641: `ALTA` equivale a `add`, `BAJA` a `delete`, y `CAMBIO_OFERTA` y `RELOCALIZACION` a `modify`.

No cubre otros procesos eTOM (Assurance, Billing), ni la gestión del catálogo (las ofertas son fijas y de solo lectura), ni la totalidad de Order Handling: se limita a cuatro tipos de orden con ciclo de vida simplificado, suficientes para ilustrar contrato de datos, validación de schema, reglas de negocio, máquina de estados y campos calculados.

---

## 3. Definición de los Recursos

### 3.1 Orden de Servicio

Todos los campos están presentes en toda representación de una orden. Un campo que no aplica al tipo de orden se representa con valor `null`.

| Campo | Tipo | Obligatoriedad | Origen | Mutabilidad | Descripción |
| --- | --- | --- | --- | --- | --- |
| `id` | string (UUID) | Generado por servidor | Servidor | Solo lectura | Identificador técnico único de la orden. |
| `tipo_orden` | enum | Opcional en creación. Default: `ALTA` | Cliente | Inmutable | Tipo de orden. Ver valores permitidos (Sección 3.6). |
| `com_id` | string (7 dígitos) | Obligatorio en creación | Cliente | Inmutable | Número de orden comercial, emitido por el sistema solicitante (CRM o GUI). Único entre todas las órdenes. |
| `cliente_id` | string | Obligatorio en creación | Cliente | Inmutable | Identificador del cliente solicitante. |
| `tipo_servicio` | enum | Obligatorio en creación de `ALTA`. En los demás tipos, opcional | Cliente en `ALTA`; servidor en los demás tipos | Inmutable | Servicio sobre el que actúa la orden. En `BAJA`, `CAMBIO_OFERTA` y `RELOCALIZACION` se deriva de la suscripción. |
| `offer_id` | string (6 dígitos) | Obligatorio en creación de `ALTA` y `CAMBIO_OFERTA` | Cliente | Inmutable | Oferta contratada (`ALTA`) u oferta nueva (`CAMBIO_OFERTA`). `null` en `BAJA` y `RELOCALIZACION`. |
| `subscription_id` | string (8 dígitos) | Obligatorio en creación de `BAJA`, `CAMBIO_OFERTA` y `RELOCALIZACION` | Servidor en `ALTA`; cliente en los demás tipos | Inmutable | Suscripción sobre la que actúa la orden. En `ALTA` la genera el servidor (Sección 4.3). |
| `punto_actual` | objeto Punto | Obligatorio en creación de `RELOCALIZACION` | Cliente | Inmutable | Ubicación actual del punto de red. Ver Sección 3.2. `null` en los demás tipos. |
| `punto_destino` | objeto Punto | Obligatorio en creación de `RELOCALIZACION` | Cliente | Inmutable | Ubicación deseada del punto de red. Ver Sección 3.2. `null` en los demás tipos. |
| `distancia_m` | number | Calculado por servidor | Servidor | Solo lectura | Metros de cable a tender. Ver Sección 4.4. `null` en los demás tipos. |
| `duracion_estimada_ms` | integer | Calculado por servidor | Servidor | Solo lectura | Duración estimada del trabajo, en milisegundos. Ver Sección 4.4. `null` en los demás tipos. |
| `prioridad` | enum | Opcional en creación. Default: `MEDIA` | Cliente | Editable | Ver valores permitidos (Sección 3.6). |
| `descripcion` | string | Opcional en creación. Default: cadena vacía | Cliente | Editable | Detalle libre de la solicitud. |
| `estado` | enum | Controlado por servidor | Servidor | Solo cambia por transición de estado | Ver máquina de estados (Sección 5.1). |
| `fecha_creacion` | string (ISO 8601) | Generado por servidor | Servidor | Solo lectura | Fecha y hora de creación, en UTC. |
| `fecha_actualizacion` | string (ISO 8601) | Generado por servidor | Servidor | Solo lectura | Se actualiza en cada transición de `estado` y en cada modificación de un campo editable. |

**Mutabilidad.** Un campo **inmutable** se fija en la creación y no cambia durante la vida de la orden. Un campo **editable** puede modificarse mientras la orden no esté en estado terminal. Un campo de **solo lectura** lo genera o calcula el servidor; el cliente nunca lo establece.

**Representación expandida.** A solicitud del cliente (mecanismo definido en el Contrato Operativo), la representación de una orden incluye además el campo `oferta`, con la representación completa de la Oferta referida por `offer_id` (Sección 3.4), o `null` si `offer_id` es `null`. Sin esa solicitud, el campo `oferta` no se incluye.

#### Campos obligatorios por tipo de orden en la creación

| Campo | `ALTA` | `BAJA` | `CAMBIO_OFERTA` | `RELOCALIZACION` |
| --- | --- | --- | --- | --- |
| `com_id` | Obligatorio | Obligatorio | Obligatorio | Obligatorio |
| `cliente_id` | Obligatorio | Obligatorio | Obligatorio | Obligatorio |
| `tipo_servicio` | Obligatorio | Opcional (RN-06) | Opcional (RN-06) | Opcional (RN-06) |
| `offer_id` | Obligatorio | No aplica | Obligatorio | No aplica |
| `subscription_id` | No aplica (lo genera el servidor) | Obligatorio | Obligatorio | Obligatorio |
| `punto_actual`, `punto_destino` | No aplica | No aplica | No aplica | Obligatorio |
| `prioridad`, `descripcion` | Opcional | Opcional | Opcional | Opcional |

### 3.2 Estructura Punto

Ubicación de un punto de red sobre el plano del hogar, en metros. El eje `x` crece hacia el este y el eje `y` crece hacia el norte.

| Campo | Tipo | Obligatoriedad | Descripción |
| --- | --- | --- | --- |
| `x` | number | Obligatorio | Coordenada este-oeste, en metros. Rango: 0 a 100. Admite decimales. |
| `y` | number | Obligatorio | Coordenada norte-sur, en metros. Rango: 0 a 100. Admite decimales. |
| `referencia` | string | Opcional | Nombre del recinto (ej. "Living"). Máximo 40 caracteres. Se usa en los textos de los pasos de trabajo. |

### 3.3 Suscripción (solo lectura)

Instancia de un servicio contratado por un cliente. Una suscripción corresponde a un único servicio. Un cliente puede tener varias suscripciones, incluso del mismo servicio. El cliente no crea ni modifica suscripciones directamente: se crean y cambian exclusivamente como efecto de las órdenes (Sección 5.3).

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `subscription_id` | string (8 dígitos) | Identificador único. Ver formato en Sección 3.5. |
| `cliente_id` | string | Titular de la suscripción: el `cliente_id` de la orden de `ALTA` que la creó. |
| `tipo_servicio` | enum | Servicio de la suscripción. Coincide con el prefijo de `subscription_id`. |
| `offer_id` | string (6 dígitos) | Oferta vigente. Se fija en el `ALTA` y cambia al completarse un `CAMBIO_OFERTA`. |
| `estado` | enum | Estado de la suscripción. Ver máquina de estados (Sección 5.2). |
| `orden_alta_id` | string (UUID) | `id` de la orden de `ALTA` que creó la suscripción. |
| `fecha_creacion` | string (ISO 8601) | Fecha y hora de creación de la suscripción (creación del `ALTA`). |
| `fecha_actualizacion` | string (ISO 8601) | Se actualiza cada vez que una orden produce un efecto sobre la suscripción. |

### 3.4 Oferta (solo lectura)

Oferta comercial del catálogo. El catálogo es fijo en esta versión del contrato.

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `offer_id` | string (6 dígitos) | Identificador único. Ver formato en Sección 3.5. |
| `nombre` | string | Nombre comercial de la oferta. |
| `tipo_servicio` | enum | Servicio al que pertenece la oferta. Coincide con el prefijo de `offer_id`. |

#### Catálogo vigente

| `offer_id` | `nombre` | `tipo_servicio` |
| --- | --- | --- |
| `200101` | Fibra 300 Mbps | `INTERNET` |
| `200102` | Fibra 600 Mbps | `INTERNET` |
| `200103` | Fibra 1 Gbps | `INTERNET` |
| `300101` | TV Básico | `TV` |
| `300102` | TV Premium | `TV` |
| `300103` | TV Premium con Deportes | `TV` |
| `400101` | Fija Local | `TELEFONIA` |
| `400102` | Fija Nacional Ilimitada | `TELEFONIA` |
| `400103` | Fija con Internacional | `TELEFONIA` |

### 3.5 Formato de los Identificadores

| Identificador | Formato | Emisor | Unicidad |
| --- | --- | --- | --- |
| `id` | UUID versión 4 | Servidor | Única por orden |
| `com_id` | Exactamente 7 dígitos (`0` a `9`), como string | Cliente | Única por orden (RN-01) |
| `subscription_id` | Exactamente 8 dígitos, como string: prefijo de servicio (2 dígitos) + correlativo (6 dígitos) | Servidor | Única por suscripción |
| `offer_id` | Exactamente 6 dígitos, como string: prefijo de servicio (2 dígitos) + número de oferta (4 dígitos) | Catálogo | Única en el catálogo |

Los identificadores numéricos se representan como string para conservar los ceros a la izquierda y su largo fijo.

#### Prefijo de servicio

| Prefijo | `tipo_servicio` |
| --- | --- |
| `20` | `INTERNET` |
| `30` | `TV` |
| `40` | `TELEFONIA` |

### 3.6 Valores Permitidos

| Campo | Valores |
| --- | --- |
| `tipo_orden` | `ALTA`, `BAJA`, `CAMBIO_OFERTA`, `RELOCALIZACION` |
| `tipo_servicio` | `INTERNET`, `TELEFONIA`, `TV` |
| `prioridad` | `ALTA`, `MEDIA`, `BAJA` |
| `estado` (orden) | `RECIBIDA`, `EN_PROGRESO`, `COMPLETADA`, `CANCELADA` |
| `estado` (suscripción) | `PENDIENTE`, `ACTIVA`, `ANULADA`, `BAJA` |
| `idioma` (trazabilidad) | `es`, `en` |

### 3.7 Trazabilidad de una Orden (representación de solo lectura)

Representación que reúne el historial de estados de una orden y, en una `RELOCALIZACION`, el detalle del trabajo a ejecutar. No es un recurso independiente: es una vista de la orden.

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `orden_id` | string (UUID) | `id` de la orden. |
| `com_id` | string | `com_id` de la orden. |
| `tipo_orden` | enum | Tipo de la orden. |
| `subscription_id` | string | Suscripción de la orden. |
| `idioma` | enum | Idioma en que se generaron los textos de `trabajo.pasos`. Default: `en`. El mecanismo para solicitar otro idioma se define en el Contrato Operativo. |
| `historial` | lista de Entrada de historial | Una entrada por cada estado que ha tenido la orden, en orden cronológico, comenzando por `RECIBIDA`. |
| `trabajo` | objeto Trabajo | Detalle del trabajo de una `RELOCALIZACION`. `null` en los demás tipos. |

**Entrada de historial**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `estado` | enum | Estado alcanzado. |
| `fecha` | string (ISO 8601) | Fecha y hora en que la orden alcanzó ese estado, en UTC. |

**Trabajo**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `distancia_m` | number | Igual a `distancia_m` de la orden. |
| `duracion_estimada_ms` | integer | Igual a `duracion_estimada_ms` de la orden. |
| `pasos` | lista de Paso de trabajo | Pasos en orden de ejecución. Ver Sección 4.4. |

**Paso de trabajo**

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `secuencia` | integer | Número de paso, desde 1. |
| `texto` | string | Instrucción del paso, en el idioma indicado por `idioma`. |
| `distancia_m` | number | Metros de cable del paso. `0` en los pasos sin tendido. |
| `duracion_ms` | integer | Duración del paso, en milisegundos. |

---

## 4. Reglas de Validación del Contrato

Las reglas se identifican con un código para que el Contrato Operativo y de Protocolo (Sección 7 de ese documento) asigne a cada una el código de estado HTTP y el código de error con que se comunica su violación. Este documento define qué es válido; no define cómo se comunica un fallo.

Las operaciones se nombran por su efecto: **creación**, **reemplazo completo**, **actualización parcial**, **transición de estado** y **cancelación**. El método HTTP de cada una se define en el Contrato Operativo, Sección 5.

### 4.1 Reglas de Schema (RV)

Se evalúan sobre la estructura de la representación recibida, sin consultar datos almacenados.

| Código | Regla |
| --- | --- |
| RV-01 | `tipo_orden`, si se envía, pertenece a los valores permitidos. Si se omite, se asume `ALTA`. |
| RV-02 | En la creación, los campos obligatorios para el tipo de orden (tabla de la Sección 3.1) están presentes. |
| RV-03 | `com_id` tiene exactamente 7 dígitos; `offer_id`, exactamente 6; `subscription_id`, exactamente 8 (Sección 3.5). |
| RV-04 | `cliente_id` es un string no vacío. |
| RV-05 | `tipo_servicio`, `prioridad` y `estado` pertenecen exactamente a los valores permitidos (Sección 3.6). |
| RV-06 | `punto_actual` y `punto_destino` cumplen la estructura Punto: `x` e `y` numéricos entre 0 y 100; `referencia`, si se envía, string de hasta 40 caracteres. |
| RV-07 | En el reemplazo completo, `prioridad` y `descripcion` están presentes. |
| RV-08 | En la actualización parcial, el cuerpo contiene al menos uno de `estado` y `descripcion`, y ningún otro campo. |
| RV-09 | Los campos de solo lectura (`id`, `estado` en la creación, `distancia_m`, `duracion_estimada_ms`, `fecha_creacion`, `fecha_actualizacion`) enviados en la creación o en el reemplazo completo se ignoran: el servidor mantiene o genera sus propios valores. No es un error. |
| RV-10 | Los campos que no aplican al tipo de orden (tabla de la Sección 3.1) enviados en la creación se ignoran: `offer_id` en `BAJA` y `RELOCALIZACION`, `subscription_id` en `ALTA`, puntos en tipos distintos de `RELOCALIZACION`. No es un error. |

### 4.2 Reglas de Negocio (RN)

Se evalúan contra los datos almacenados. Una representación puede ser válida como dato (cumple RV) e inválida como regla de negocio.

| Código | Regla | Aplica a | Momento de evaluación |
| --- | --- | --- | --- |
| RN-01 | `com_id` no existe en ninguna otra orden. | Todos los tipos | Creación |
| RN-02 | `offer_id` existe en el catálogo (Sección 3.4). | `ALTA`, `CAMBIO_OFERTA` | Creación |
| RN-03 | El prefijo de `offer_id` corresponde al servicio: al `tipo_servicio` de la orden en `ALTA`, o al servicio de la suscripción en `CAMBIO_OFERTA`. | `ALTA`, `CAMBIO_OFERTA` | Creación |
| RN-04 | `subscription_id` existe. | `BAJA`, `CAMBIO_OFERTA`, `RELOCALIZACION` | Creación |
| RN-05 | `cliente_id` coincide con el titular de la suscripción. | `BAJA`, `CAMBIO_OFERTA`, `RELOCALIZACION` | Creación |
| RN-06 | `tipo_servicio`, si se envía, coincide con el servicio de la suscripción. | `BAJA`, `CAMBIO_OFERTA`, `RELOCALIZACION` | Creación |
| RN-07 | La suscripción está en estado `ACTIVA`. | `BAJA`, `CAMBIO_OFERTA`, `RELOCALIZACION` | Creación y transición a `EN_PROGRESO` |
| RN-08 | `offer_id` es distinto de la oferta vigente de la suscripción. | `CAMBIO_OFERTA` | Creación y transición a `EN_PROGRESO` |
| RN-09 | `punto_actual` y `punto_destino` son distintos (distancia mayor que cero). | `RELOCALIZACION` | Creación |
| RN-10 | No existe otra orden de la misma suscripción en estado `EN_PROGRESO`. | Todos los tipos | Transición a `EN_PROGRESO` |
| RN-11 | La transición solicitada está permitida por la máquina de estados de la orden (Sección 5.1). | Todos los tipos | Transición de estado |
| RN-12 | Una orden en estado terminal (`COMPLETADA` o `CANCELADA`) no admite reemplazo completo, actualización parcial ni cancelación. | Todos los tipos | Reemplazo, actualización y cancelación |
| RN-13 | En el reemplazo completo, los campos inmutables que se incluyan coinciden con sus valores vigentes. | Todos los tipos | Reemplazo completo |

RN-07 y RN-08 se evalúan dos veces porque la suscripción puede cambiar mientras una orden espera en `RECIBIDA` (Sección 5.4).

### 4.3 Generación de Identificadores

- `id`: UUID versión 4, generado al crear la orden.
- `subscription_id`: se genera al crear una orden de `ALTA`, antes de responder. Se compone del prefijo del `tipo_servicio` de la orden y de un correlativo de 6 dígitos con ceros a la izquierda. Existe un correlativo independiente por servicio, que comienza en `000001`. Un número emitido nunca se reutiliza, aunque el `ALTA` se cancele. Ejemplo: el primer `ALTA` de `INTERNET` genera `20000001`; el primero de `TV`, `30000001`.

### 4.4 Campos Calculados de la Relocalización

Se calculan en la creación de una `RELOCALIZACION` y no cambian después. Sean `dx = punto_destino.x − punto_actual.x` y `dy = punto_destino.y − punto_actual.y`.

**Pasos de trabajo.** Se generan en este orden. Un paso de tendido cuya distancia es cero se omite y los pasos se renumeran consecutivamente.

| Paso | Condición | `distancia_m` | `duracion_ms` |
| --- | --- | --- | --- |
| Desconexión | Siempre | `0` | 600 000 (10 minutos) |
| Tendido en el eje este-oeste | `dx` distinto de cero | valor absoluto de `dx`, redondeado a 3 decimales | `distancia_m` del paso × 120 000 (2 minutos por metro), redondeado al entero |
| Tendido en el eje norte-sur | `dy` distinto de cero | valor absoluto de `dy`, redondeado a 3 decimales | `distancia_m` del paso × 120 000, redondeado al entero |
| Conexión y verificación | Siempre | `0` | 900 000 (15 minutos) |

**Totales.**

- `distancia_m` = suma de `distancia_m` de los pasos, redondeada a 3 decimales (distancia en recorrido ortogonal, porque el cable sigue las paredes).
- `duracion_estimada_ms` = suma de `duracion_ms` de los pasos.

**Textos de los pasos.** El texto entre paréntesis se incluye solo si el punto tiene `referencia`.

| Paso | `es` | `en` |
| --- | --- | --- |
| Desconexión | Desconectar el equipo en el punto actual (`<referencia>`) | Disconnect the device at the current point (`<referencia>`) |
| Tendido, `dx` > 0 | Tender cable hacia el este | Run cable to the east |
| Tendido, `dx` < 0 | Tender cable hacia el oeste | Run cable to the west |
| Tendido, `dy` > 0 | Tender cable hacia el norte | Run cable to the north |
| Tendido, `dy` < 0 | Tender cable hacia el sur | Run cable to the south |
| Conexión y verificación | Conectar y verificar el equipo en el punto de destino (`<referencia>`) | Connect and test the device at the destination point (`<referencia>`) |

`<referencia>` representa el valor del campo `referencia` del punto correspondiente.

---

## 5. Máquinas de Estados

### 5.1 Estado de la Orden

```
RECIBIDA ──► EN_PROGRESO ──► COMPLETADA
    │              │
    └──────────────┴──► CANCELADA
```

| Desde | Hacia | Válida |
| --- | --- | --- |
| RECIBIDA | EN_PROGRESO | Sí, sujeta a RN-07, RN-08 y RN-10 |
| EN_PROGRESO | COMPLETADA | Sí |
| RECIBIDA | CANCELADA | Sí |
| EN_PROGRESO | CANCELADA | Sí |
| COMPLETADA | cualquiera | No |
| CANCELADA | cualquiera | No |

La máquina es la misma para los cuatro tipos de orden. Una transición no listada es válida como dato (el valor de `estado` está permitido por el schema) pero inválida como regla de negocio (RN-11). Esta distinción es intencional: separa la validación de schema de la validación de reglas de negocio.

### 5.2 Estado de la Suscripción

```
PENDIENTE ──► ACTIVA ──► BAJA
    │
    └──► ANULADA
```

| Desde | Hacia | Causa |
| --- | --- | --- |
| (no existe) | PENDIENTE | Creación de una orden de `ALTA` |
| PENDIENTE | ACTIVA | El `ALTA` pasa a `COMPLETADA` |
| PENDIENTE | ANULADA | El `ALTA` pasa a `CANCELADA` |
| ACTIVA | BAJA | Una `BAJA` pasa a `COMPLETADA` |

`ANULADA` y `BAJA` son estados terminales. El cliente nunca transiciona una suscripción directamente.

### 5.3 Efectos de las Órdenes sobre la Suscripción

| Tipo de orden | Al pasar a `COMPLETADA` | Al pasar a `CANCELADA` |
| --- | --- | --- |
| `ALTA` | Suscripción pasa a `ACTIVA` | Suscripción pasa a `ANULADA` |
| `BAJA` | Suscripción pasa a `BAJA` | Sin efecto |
| `CAMBIO_OFERTA` | `offer_id` de la suscripción pasa a ser el `offer_id` de la orden | Sin efecto |
| `RELOCALIZACION` | Sin efecto sobre la suscripción | Sin efecto |

Cada efecto actualiza `fecha_actualizacion` de la suscripción.

### 5.4 Serialización de la Ejecución

Sobre una misma suscripción pueden existir varias órdenes en `RECIBIDA` al mismo tiempo, pero solo una puede estar en `EN_PROGRESO` (RN-10). El estado `EN_PROGRESO` funciona como un bloqueo de ejecución: mientras una orden lo ocupa, ninguna otra orden de la suscripción puede iniciar su ejecución, y por lo tanto la suscripción no cambia hasta que esa orden se complete o se cancele.

Como consecuencia, una orden que esperaba en `RECIBIDA` puede quedar inválida por el efecto de otra. Por eso RN-07 y RN-08 se reevalúan al transicionar a `EN_PROGRESO`. Ejemplo: una `RELOCALIZACION` en `RECIBIDA` no puede iniciarse si, mientras esperaba, se completó una `BAJA` de la misma suscripción. Esa orden solo puede cancelarse.

---

## 6. Ejemplos de Representación de los Recursos

Los valores son ilustrativos. En las actividades del curso, `cliente_id` se reemplaza por el RUT del estudiante, sin puntos ni guion.

**6.1 Creación de un `ALTA`** — solo campos que el cliente puede enviar:

```json
{
  "tipo_orden": "ALTA",
  "com_id": "1000001",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "offer_id": "200102",
  "prioridad": "ALTA",
  "descripcion": "Alta de Fibra 600 Mbps residencial"
}
```

**6.2 Representación completa del `ALTA`** tras la creación:

```json
{
  "id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
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
  "prioridad": "ALTA",
  "descripcion": "Alta de Fibra 600 Mbps residencial",
  "estado": "RECIBIDA",
  "fecha_creacion": "2026-10-05T13:00:00Z",
  "fecha_actualizacion": "2026-10-05T13:00:00Z"
}
```

**6.3 Representación expandida** del mismo `ALTA` (solo los campos que cambian respecto de 6.2):

```json
{
  "id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
  "offer_id": "200102",
  "oferta": {
    "offer_id": "200102",
    "nombre": "Fibra 600 Mbps",
    "tipo_servicio": "INTERNET"
  }
}
```

**6.4 Creación de una `RELOCALIZACION`** sobre la suscripción ya `ACTIVA`:

```json
{
  "tipo_orden": "RELOCALIZACION",
  "com_id": "1000002",
  "cliente_id": "CL-10457",
  "subscription_id": "20000001",
  "punto_actual": { "x": 2.5, "y": 1.75, "referencia": "Living" },
  "punto_destino": { "x": 6.125, "y": 4.5, "referencia": "Dormitorio 2" },
  "descripcion": "Traslado del router al dormitorio"
}
```

**6.5 Representación completa de la `RELOCALIZACION`** tras la creación:

```json
{
  "id": "7c1d4b2e-5a9f-4e3b-8d6c-2f0a9b8e7d14",
  "tipo_orden": "RELOCALIZACION",
  "com_id": "1000002",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "offer_id": null,
  "subscription_id": "20000001",
  "punto_actual": { "x": 2.5, "y": 1.75, "referencia": "Living" },
  "punto_destino": { "x": 6.125, "y": 4.5, "referencia": "Dormitorio 2" },
  "distancia_m": 6.375,
  "duracion_estimada_ms": 2265000,
  "prioridad": "MEDIA",
  "descripcion": "Traslado del router al dormitorio",
  "estado": "RECIBIDA",
  "fecha_creacion": "2026-10-05T14:10:00Z",
  "fecha_actualizacion": "2026-10-05T14:10:00Z"
}
```

**6.6 Trazabilidad de la `RELOCALIZACION`**, en idioma `es`, después de iniciar su ejecución:

```json
{
  "orden_id": "7c1d4b2e-5a9f-4e3b-8d6c-2f0a9b8e7d14",
  "com_id": "1000002",
  "tipo_orden": "RELOCALIZACION",
  "subscription_id": "20000001",
  "idioma": "es",
  "historial": [
    { "estado": "RECIBIDA", "fecha": "2026-10-05T14:10:00Z" },
    { "estado": "EN_PROGRESO", "fecha": "2026-10-05T14:20:00Z" }
  ],
  "trabajo": {
    "distancia_m": 6.375,
    "duracion_estimada_ms": 2265000,
    "pasos": [
      { "secuencia": 1, "texto": "Desconectar el equipo en el punto actual (Living)", "distancia_m": 0, "duracion_ms": 600000 },
      { "secuencia": 2, "texto": "Tender cable hacia el este", "distancia_m": 3.625, "duracion_ms": 435000 },
      { "secuencia": 3, "texto": "Tender cable hacia el norte", "distancia_m": 2.75, "duracion_ms": 330000 },
      { "secuencia": 4, "texto": "Conectar y verificar el equipo en el punto de destino (Dormitorio 2)", "distancia_m": 0, "duracion_ms": 900000 }
    ]
  }
}
```

Lectura de los valores: 6,375 m equivalen a 637,5 cm; 2 265 000 ms equivalen a 00:37:45.

**6.7 Trazabilidad de un `ALTA`** completado (sin trabajo de relocalización):

```json
{
  "orden_id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
  "com_id": "1000001",
  "tipo_orden": "ALTA",
  "subscription_id": "20000001",
  "idioma": "en",
  "historial": [
    { "estado": "RECIBIDA", "fecha": "2026-10-05T13:00:00Z" },
    { "estado": "EN_PROGRESO", "fecha": "2026-10-05T13:05:00Z" },
    { "estado": "COMPLETADA", "fecha": "2026-10-05T13:30:00Z" }
  ],
  "trabajo": null
}
```

**6.8 Creación de un `CAMBIO_OFERTA`** y de una `BAJA`:

```json
{
  "tipo_orden": "CAMBIO_OFERTA",
  "com_id": "1000003",
  "cliente_id": "CL-10457",
  "subscription_id": "20000001",
  "offer_id": "200103",
  "descripcion": "Upgrade a Fibra 1 Gbps"
}
```

```json
{
  "tipo_orden": "BAJA",
  "com_id": "1000004",
  "cliente_id": "CL-10457",
  "subscription_id": "20000001",
  "descripcion": "Baja por cambio de domicilio"
}
```

**6.9 Reemplazo completo y actualización parcial** de una orden no terminal:

```json
{
  "prioridad": "ALTA",
  "descripcion": "Traslado del router al dormitorio principal"
}
```

```json
{
  "descripcion": "Traslado del router al dormitorio principal"
}
```

**6.10 Suscripción**, después de completarse el `ALTA`:

```json
{
  "subscription_id": "20000001",
  "cliente_id": "CL-10457",
  "tipo_servicio": "INTERNET",
  "offer_id": "200102",
  "estado": "ACTIVA",
  "orden_alta_id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
  "fecha_creacion": "2026-10-05T13:00:00Z",
  "fecha_actualizacion": "2026-10-05T13:30:00Z"
}
```

**6.11 Oferta**:

```json
{
  "offer_id": "200102",
  "nombre": "Fibra 600 Mbps",
  "tipo_servicio": "INTERNET"
}
```

---

## 7. Política de Versionado del Contrato

- Agregar un campo **opcional** nuevo: cambio menor, no rompe clientes existentes.
- Eliminar un campo, renombrarlo, o cambiar su tipo u obligatoriedad: cambio mayor, rompe clientes existentes. Requiere nueva versión del contrato y coordinación con el Contrato Operativo, que expone la versión en la ruta base.
- Esta ficha documenta la versión **2.0** del contrato.

La versión 2.0 es un cambio mayor respecto de 1.x por estos cambios incompatibles:

| Cambio | Efecto sobre un cliente 1.x |
| --- | --- |
| `com_id` pasa a ser obligatorio en la creación | Una creación sin `com_id` deja de ser válida (RV-02) |
| `cliente_id` y `tipo_servicio` pasan a ser inmutables | El reemplazo completo ya no los modifica (RN-13) |
| El reemplazo completo exige `prioridad` y `descripcion` | Un reemplazo con solo `cliente_id` y `tipo_servicio` deja de ser válido (RV-07) |
| La actualización parcial admite `descripcion`, además de `estado` | Cambia el alcance de la operación (RV-08) |
| `ALTA` exige `offer_id` | Una creación sin oferta deja de ser válida (RV-02) |

---

## 8. Glosario

| Término | Definición |
| --- | --- |
| Contrato de Datos (Data Contract) | Especificación formal de la estructura, tipos y reglas de validación de un recurso, independiente de su implementación. |
| Schema | Sinónimo técnico de Contrato de Datos en el contexto de APIs; también usado para referirse a su representación formal (ej. JSON Schema). |
| Campo de solo lectura | Campo cuyo valor es generado o calculado por el servidor; el cliente no puede establecerlo ni modificarlo. |
| Campo inmutable | Campo que el cliente establece en la creación y que no cambia durante la vida del recurso. |
| Campo editable | Campo que el cliente puede modificar mientras la orden no esté en estado terminal. |
| Campo calculado | Campo de solo lectura cuyo valor el servidor deriva de otros campos (ej. `distancia_m`). |
| Enum | Conjunto cerrado y finito de valores permitidos para un campo. |
| Orden comercial (`com_id`) | Número con que el sistema comercial solicitante (CRM o GUI) identifica su pedido. Distinto del `id` técnico que asigna el SOM. |
| Suscripción | Instancia de un servicio contratado por un cliente, creada por un `ALTA` y modificada por las órdenes posteriores. |
| Oferta | Producto comercial del catálogo que define qué se contrata dentro de un servicio. |
| Relocalización | Traslado de un punto de red dentro del hogar del cliente, desde un punto actual a un punto de destino. |
| Recorrido ortogonal | Distancia medida sumando los desplazamientos en cada eje, como un cable que sigue las paredes. |
| Serialización de la ejecución | Regla que permite a lo más una orden en ejecución por suscripción a la vez (RN-10). |
| Estado terminal | Estado desde el cual no hay transiciones permitidas. |
| Contrato Operativo | Documento complementario que define protocolo, transporte, autenticación, rutas y códigos de estado — ver ficha asociada. |

---

*Documento de referencia — no es un procedimiento (MOP). Se actualiza únicamente cuando cambia la definición de los recursos.*
