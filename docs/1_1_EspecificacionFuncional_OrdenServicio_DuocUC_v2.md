<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">Especificación Funcional — Orden de Servicio</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Especificación Funcional — Orden de Servicio (API Demo eTOM/SOM) |
| Versión | 3.0 |
| Fecha | 05/10/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | EA2 — Fundamentos y Consumo de APIs (2.3 / 2.4); base de la actividad formativa 2.4.2 |
| Documentos asociados | DisenoFuncional_OrdenServicio_DuocUC.md (2.0), Contrato_Datos_OrdenServicio_DuocUC.md (2.0), Contrato_Operativo_OrdenServicio_DuocUC.md (2.0) |

### Lista de Distribución

| De | Fecha | Email |
| --- | --- | --- |
| Pablo Moscoso (Docente) | 05/10/2026 | pablo.moscoso@profesor.duoc.cl |

| Para | Acción | Fecha Comprometida | Email |
| --- | --- | --- | --- |
| `<ENCARGADO_DE_LINEA>` | Aprobación | `<FECHA_COMPROMETIDA>` | `<EMAIL_ENCARGADO_DE_LINEA>` |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |
| 2.0 | 21/09/2026 | Pablo Moscoso | Cambio mayor, coordinado con Contrato Operativo v1.3: Sección 3 (el Sistema Cliente cuenta con implementación de referencia `crm-som`, canal CRM); Sección 4 (abreviación CRM); Sección 5 (casos de uso de notificación asíncrona); Sección 8 (autenticación diferenciada por canal, alcance real de la integración CRM); Sección 9 (referencia a `crm_som.py`) |
| 3.0 | 05/10/2026 | Pablo Moscoso | Cambio mayor, coordinado con Contrato de Datos 2.0, Contrato Operativo 2.0 y Diseño Funcional 2.0. Sección 2: contexto ampliado a suscripciones, catálogo de ofertas y cuatro tipos de orden. Sección 3: nuevo actor Técnico de Terreno; el Sistema Cliente identifica sus pedidos con `com_id`; `crm-som` ya se despliega con los estudiantes (corrige la versión 2.0, que lo limitaba al docente); el Actor de Soporte inicia sesión con usuario y contraseña. Sección 4: abreviaciones COM, TMF638, TMF620, UUID y OpenAPI. Sección 5: casos de uso reescritos por tipo de orden, más órdenes encoladas, reenvío accidental y carga masiva. Sección 6: reglas de negocio de suscripciones, ofertas, titularidad y ejecución serializada. Sección 7: correspondencia con TMF638 y TMF620. Sección 8: alcance y dependencias actualizados. Sección 9: referencias numeradas |

---

## 2. Propósito y Contexto de Negocio

Este documento describe, en términos de negocio, el propósito y el alcance funcional del API demo de Orden de Servicio: por qué existe, quién lo usa y qué problema resuelve. No repite el detalle técnico documentado en el Contrato de Datos, el Contrato Operativo y de Protocolo y el Diseño Funcional; se ubica un nivel por encima de ellos y los referencia.

Un proveedor de telecomunicaciones vende servicios (internet, televisión, telefonía) que el cliente contrata, modifica y da de baja a lo largo del tiempo. Cada uno de esos pedidos llega desde el sistema comercial como una **orden** y debe cumplirse en terreno antes de reflejarse en el inventario de servicios del cliente. El sistema permite:

- **Contratar** un servicio a partir de una oferta del catálogo, lo que crea una **suscripción** del cliente.
- **Cambiar la oferta** de una suscripción, **dar de baja** el servicio, o **relocalizar** un punto de red dentro del hogar.
- **Dar seguimiento** a cada orden, desde su recepción hasta su cumplimiento o cancelación, con su historial y, en una relocalización, los pasos de trabajo, la distancia de cable y la duración estimada.
- **Proteger la consistencia** del inventario: una orden solo actúa sobre una suscripción activa del mismo cliente, y las órdenes de una misma suscripción se ejecutan de a una.

Replica, en una versión simplificada con fines educativos, el tipo de interacción que resuelve un sistema real de Service Order Management (SOM) dentro de un proveedor de telecomunicaciones.

En el curso CUY6142, el sistema permite al estudiante observar una API desde el lado que expone el servicio (servidor desplegado en su propia instancia) y desde el lado que lo consume (Postman, `curl` y scripts Python). Es la base de la actividad formativa 2.4.2, que ensaya con este sistema la misma mecánica de consumo de APIs que se evalúa después con otras APIs.

---

## 3. Actores

| Actor | Naturaleza | Rol |
| --- | --- | --- |
| Sistema Cliente | Automatizado (negocio) | Sistema comercial externo (CRM o canal de venta) que emite las órdenes de forma programática y las identifica con su propio número de orden comercial (`com_id`). Consulta el catálogo de ofertas y las suscripciones del cliente, crea órdenes de los cuatro tipos, las consulta y las cancela. No ejecuta el cumplimiento: no hace avanzar el estado de las órdenes. Recibe la notificación asíncrona de cada cambio de estado (Contrato Operativo, Sección 6). Se autentica con la clave fija del canal CRM. Cuenta con una implementación de referencia (`crm-som`), que los estudiantes despliegan junto al SOM en el MOP de la Semana 8. |
| Actor de Soporte | Manual (negocio, real) | Personal técnico que opera el SOM directamente con Postman o `curl`: hace avanzar las órdenes por las etapas de cumplimiento, consulta su trazabilidad, concilia órdenes cuya notificación no llegó al Sistema Cliente y cancela órdenes que ya no pueden ejecutarse. Inicia sesión con usuario y contraseña (canal GUI). Refleja un patrón real de operación, no una simplificación pedagógica. |
| Técnico de Terreno | Manual (negocio, real) | Ejecuta en el hogar del cliente el trabajo de una orden (instalación, retiro, relocalización). No interactúa con el API en esta versión: recibe los pasos de trabajo de una relocalización a través del Actor de Soporte, y este informa al SOM el avance (`EN_PROGRESO`, `COMPLETADA`). |
| Estudiante / Docente | Pedagógico (curso) | En la actividad 2.4.2, el estudiante asume dos roles reales: el del Sistema Cliente, cuando crea órdenes desde Postman o desde un script Python (por ejemplo, una carga masiva), y el del Actor de Soporte, cuando hace avanzar las órdenes y consulta su trazabilidad. Ambos replican flujos de trabajo reales, no inventados para la clase. |

---

## 4. Definiciones y Abreviaciones

| Abreviación | Descripción |
| --- | --- |
| API | Application Programming Interface |
| SOM | Service Order Management — gestión de órdenes de servicio |
| COM | Commercial Order Management — capa comercial que emite la orden; origen del `com_id` |
| CRM | Customer Relationship Management |
| eTOM | enhanced Telecom Operations Map — marco de procesos de negocio de TM Forum |
| TMF641 | Service Ordering Management — API abierto de TM Forum |
| TMF638 | Service Inventory Management — API abierto de TM Forum |
| TMF620 | Product Catalog Management — API abierto de TM Forum |
| REST | Representational State Transfer |
| JSON | JavaScript Object Notation |
| UUID | Universally Unique Identifier — identificador técnico de cada orden |
| OpenAPI | Especificación estándar para describir una API REST; base de la documentación navegable del servicio |
| ICD | Interface Control Document — equivalente de industria de las Fichas de Contrato de este curso |

---

## 5. Casos de Uso

Las rutas se indican relativas a la base `/api/v2`. Las reglas de negocio citadas (RN-xx) están definidas en el Contrato de Datos, Sección 4.2.

| Escenario | Secuencia de llamadas al API | Sección de referencia |
| --- | --- | --- |
| Inicio de sesión del Actor de Soporte | Actor de Soporte: `POST /loginViaBasic` → usa el token en las llamadas siguientes | Contrato Operativo, Sección 4.2 |
| Elección de una oferta del catálogo | Sistema Cliente: `GET /ofertas?q=...` → `GET /ofertas/{offer_id}` | Contrato Operativo, Sección 5.2 |
| Contratación de un servicio | Sistema Cliente: `POST /ordenes` (`ALTA`) → recibe el `subscription_id` de la nueva suscripción | Contrato Operativo, Sección 5.1; Contrato de Datos, Sección 4.3 |
| Cumplimiento de una orden | Actor de Soporte: `PATCH /ordenes/{id}` (`RECIBIDA` → `EN_PROGRESO` → `COMPLETADA`) → el Sistema Cliente recibe una notificación por cada cambio | Contrato de Datos, Secciones 5.1 y 5.3; Contrato Operativo, Sección 6 |
| Identificación de la suscripción de un cliente con varios servicios | Sistema Cliente: `GET /suscripciones?cliente_id=...&tipo_servicio=...` | Contrato Operativo, Sección 5.2 |
| Cambio de oferta | Sistema Cliente: `GET /suscripciones/{subscription_id}` (oferta vigente) → `GET /ofertas?tipo_servicio=...` → `POST /ordenes` (`CAMBIO_OFERTA`) | Contrato de Datos, RN-03 y RN-08 |
| Relocalización de un punto de red | Sistema Cliente: `POST /ordenes` (`RELOCALIZACION`) → Actor de Soporte: `GET /ordenes/{id}/trazabilidad?idioma=es` (pasos para el Técnico de Terreno) → `PATCH` hasta `COMPLETADA` | Contrato de Datos, Sección 4.4 |
| Baja de un servicio | Sistema Cliente: `POST /ordenes` (`BAJA`) → Actor de Soporte: `PATCH` hasta `COMPLETADA` → la suscripción queda en `BAJA` | Contrato de Datos, Sección 5.2 |
| Seguimiento de las órdenes pendientes | Actor de Soporte: `GET /ordenes?estado=RECIBIDA&estado=EN_PROGRESO` → `GET /ordenes/{id}/trazabilidad` | Contrato Operativo, Sección 5.2 |
| Carga masiva de órdenes | Sistema Cliente (script): `POST /ordenes` repetido → `GET /ordenes?page=...` recorriendo las páginas según `X-Total-Count` | Contrato Operativo, Sección 5.2 |
| Actualización de los datos de una orden en curso | Actor de Soporte: `PATCH /ordenes/{id}` (solo `descripcion`) o `PUT /ordenes/{id}` (prioridad y descripción) | Contrato Operativo, Sección 5.3 |
| Cancelación de una orden | Sistema Cliente o Actor de Soporte: `DELETE /ordenes/{id}` → si es un `ALTA`, la suscripción queda `ANULADA` | Contrato de Datos, Sección 5.3 |
| Registro del receptor de notificaciones | Sistema Cliente: `POST /webhooks` | Contrato Operativo, Sección 6.2 |
| Conciliación de notificaciones no entregadas | Actor de Soporte: `GET /webhooks/fallos` → `GET /ordenes/{orden_id}` por cada entrada | Contrato Operativo, Sección 6.7 |
| Dos órdenes de la misma suscripción listas para ejecutarse | Actor de Soporte: `PATCH` de la segunda a `EN_PROGRESO` mientras la primera está en ejecución → rechazada (RN-10); completa la primera y reintenta la segunda | Contrato de Datos, Sección 5.4 |
| Orden en espera invalidada por una baja | Actor de Soporte: tras completar una `BAJA`, `PATCH` de una `RELOCALIZACION` que esperaba sobre la misma suscripción → rechazada (RN-07) → `DELETE` de la orden | Contrato de Datos, Sección 5.4 |
| Reenvío accidental de una orden comercial | Sistema Cliente: `POST /ordenes` repetido con el mismo `com_id` → rechazado (RN-01); no se crea una orden duplicada | Contrato Operativo, Sección 9 |
| Orden sobre la suscripción de otro cliente | Sistema Cliente: `POST /ordenes` con un `subscription_id` cuyo titular es otro cliente → rechazada (RN-05) | Contrato de Datos, Sección 4.2 |
| Intento de corregir una orden ya cerrada | Actor de Soporte: `PUT`, `PATCH` o `DELETE` sobre una orden `COMPLETADA` o `CANCELADA` → rechazada (RN-12) | Contrato Operativo, Sección 8.2 |

Los cinco últimos escenarios quedan fuera del flujo normal: ilustran por qué existen las reglas de ejecución de a una, de revalidación, de unicidad de la orden comercial, de titularidad y de estado terminal, no solo que existen. Tres de ellos solo ocurren desde el Actor de Soporte, que es quien hace avanzar y corrige las órdenes.

---

## 6. Reglas de Negocio

**Ciclo de vida de una orden.** Toda orden, de cualquier tipo, sigue cuatro estados. Se origina en `RECIBIDA` al crearse; avanza a `EN_PROGRESO` cuando comienza su cumplimiento en terreno; concluye en `COMPLETADA` cuando el trabajo se ejecutó, o en `CANCELADA` si el cliente o el proceso interno determinan que no debe continuar. Una orden cerrada (`COMPLETADA` o `CANCELADA`) no se modifica ni se revierte, para preservar la integridad del historial de cumplimiento.

**Tipos de orden y su efecto sobre la suscripción.**

- Un **alta** crea una suscripción nueva, pendiente hasta que el alta se completa. Si el alta se cancela, la suscripción queda anulada y su número no se reutiliza.
- Una **baja** da por terminada la suscripción cuando se completa.
- Un **cambio de oferta** reemplaza la oferta vigente de la suscripción cuando se completa. La oferta nueva debe pertenecer al mismo servicio y ser distinta de la vigente.
- Una **relocalización** traslada un punto de red dentro del mismo hogar. No cambia la suscripción; el SOM calcula los metros de cable, los pasos de trabajo y la duración estimada.

**Condiciones para actuar sobre una suscripción.** Una baja, un cambio de oferta o una relocalización solo se aceptan sobre una suscripción activa, y solo si quien la solicita es su titular. Una oferta solo puede contratarse para el servicio al que pertenece.

**Ejecución de a una.** Sobre una misma suscripción pueden esperar varias órdenes, pero solo una se ejecuta a la vez. Cuando una orden en espera va a iniciar su ejecución, se vuelven a comprobar sus condiciones, porque la suscripción pudo cambiar mientras esperaba.

**Identidad de la orden comercial.** Cada orden lleva el número de orden comercial del sistema que la emitió, único en todo el SOM. Un reenvío del mismo número se rechaza, lo que evita duplicar el trabajo en terreno.

El detalle técnico de estas reglas, sus identificadores y las máquinas de estados de la orden y de la suscripción están en el Contrato de Datos, Secciones 4 y 5.

---

## 7. Relación con el Proceso de Negocio

Este sistema simplifica, con fines educativos, el proceso eTOM **Order Handling** (Process Identifier 1.1.1.5), dentro del área de Customer Relationship Management / Operations del marco eTOM de TM Forum. Order Handling es responsable de aceptar y emitir órdenes, determinar su factibilidad y dar seguimiento a su estado hasta notificar su cumplimiento al cliente. En este sistema:

- La **aceptación** corresponde a la creación de la orden, con su validación de schema.
- La **factibilidad** se representa, de forma simplificada, con las reglas de negocio que comprueban la suscripción, la titularidad y la oferta antes de aceptar y antes de ejecutar una orden.
- El **seguimiento** corresponde a los estados, al historial y a la trazabilidad.
- La **notificación de cumplimiento** corresponde a la notificación asíncrona de cambio de estado (Contrato Operativo, Sección 6).

El sistema se alinea conceptualmente, sin pretender conformidad ni certificación, con tres APIs abiertos de TM Forum:

| Elemento del sistema | API de TM Forum | Correspondencia |
| --- | --- | --- |
| Orden y tipos de orden | TMF641 Service Ordering Management | `ALTA` equivale a la acción `add`, `BAJA` a `delete`, y `CAMBIO_OFERTA` y `RELOCALIZACION` a `modify` |
| Suscripción | TMF638 Service Inventory Management | Consulta simplificada del inventario de servicios activos del cliente |
| Oferta | TMF620 Product Catalog Management | Consulta de un catálogo fijo de ofertas comerciales |

Quedan explícitamente fuera del alcance otros procesos eTOM que un sistema SOM real suele integrar:

- **Assurance** — gestión de incidentes y tickets de soporte sobre un servicio ya activo.
- **Billing** — facturación del servicio.
- **Gestión del catálogo** — creación y mantenimiento de ofertas.

Este API cubre únicamente Order Handling, dentro del proceso más amplio de Fulfillment, con consultas de solo lectura al inventario y al catálogo.

---

## 8. Fuera de Alcance Funcional y Dependencias

### Fuera de Alcance Funcional

- Precios, facturación o cálculo de costos asociados a la orden.
- Gestión de incidentes o tickets de soporte sobre un servicio ya activo (Assurance).
- Administración del catálogo de ofertas: es fijo y de solo lectura.
- Factibilidad técnica real (cobertura de red, disponibilidad de puertos) y agendamiento de visitas del Técnico de Terreno.
- Otros tipos de orden de un SOM real: suspensión, reconexión, cambio de titular y traslado de domicilio. La relocalización cubre solo el traslado de un punto de red dentro del mismo hogar.
- Integración con sistemas CRM de mercado. La implementación de referencia propia (`crm-som`) ilustra el patrón de integración, pero no es un producto comercial.
- Gestión de usuarios o permisos individuales: la autenticación distingue canales (GUI, CRM), no personas (Contrato Operativo, Sección 4).

### Dependencias

- Prerrequisito del curso, CUY5132, cumplido.
- Actividad 2.3 (Fundamentos del Uso de APIs) cursada: este ejercicio asume manejo previo de Postman y `curl` como cliente.
- Contrato de Datos 2.0, Contrato Operativo y de Protocolo 2.0 y Diseño Funcional 2.0 vigentes: este documento no tiene sentido de forma aislada.
- Una instancia AWS por estudiante con el servicio desplegado, según el MOP de despliegue.
- Para que el Sistema Cliente opere en forma automatizada, `crm_som.py` debe estar actualizado a la versión 2.0 del API. Mientras eso no ocurra, el estudiante asume el rol del Sistema Cliente desde Postman o desde sus propios scripts.

---

## 9. Lista de Referencias

| N° | Documento | Descripción |
| --- | --- | --- |
| 1 | `DisenoFuncional_OrdenServicio_DuocUC.md` (2.0) | Diseño Funcional del sistema |
| 2 | `Contrato_Datos_OrdenServicio_DuocUC.md` (2.0) | Recursos, reglas de validación y de negocio, máquinas de estados |
| 3 | `Contrato_Operativo_OrdenServicio_DuocUC.md` (2.0) | Endpoints, autenticación, parámetros y códigos de estado |
| 4 | `som_api_demo.py` | Implementación de referencia del API |
| 5 | `crm_som.py` | Implementación de referencia del Sistema Cliente (canal CRM) |
| 6 | `MOP_OrdenServicio_Semana8_DuocUC.md` | Procedimiento de despliegue del servicio en AWS |
| 7 | `Estandar_Documentacion_API_CUY6142.md` | Estándar de documentación aplicado a este conjunto (uso interno del docente) |
| 8 | TM Forum — Business Process Framework (eTOM) | Marco de procesos de negocio de referencia de industria — tmforum.org |
| 9 | TM Forum — TMF641 Service Ordering Management | API abierto de gestión de órdenes de servicio — tmforum.org |
| 10 | TM Forum — TMF638 Service Inventory Management | API abierto de inventario de servicios — tmforum.org |
| 11 | TM Forum — TMF620 Product Catalog Management | API abierto de catálogo de productos — tmforum.org |

---

## 10. Control de Versiones de la Especificación

Un cambio que solo actualiza contexto de negocio, actores o casos de uso, sin afectar las Fichas de Contrato: cambio menor. Un cambio que requiere modificar el Contrato de Datos o el Contrato Operativo (por ejemplo, un nuevo actor con permisos distintos, o un nuevo escenario que necesita un endpoint nuevo): cambio mayor, coordinado con ambas fichas.

Esta especificación documenta la versión **3.0** del sistema, correspondiente a la versión 2.0 del API (`/api/v2`).

---

## 11. Aprobación

Esta sección resume la aceptación formal de la presente Especificación Funcional.

| Nombre | `<ENCARGADO_DE_LINEA>` |
| --- | --- |
| Cargo | Encargado de Línea, Escuela de Informática y Telecomunicaciones |
| Fecha | `<FECHA_APROBACION>` |
| Firma | ____________________________ |

---

*Documento de referencia — no es un procedimiento (MOP). Se actualiza cuando cambia el propósito, los actores o los casos de uso del sistema; los cambios técnicos se documentan en las Fichas de Contrato asociadas.*
