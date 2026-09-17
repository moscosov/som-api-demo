<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">Especificación Funcional  Orden de Servicio</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142  Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Especificación Funcional  Orden de Servicio (API Demo eTOM/SOM) |
| Versión | 1.0 |
| Fecha | 15/09/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142  Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | EA2  Fundamentos y Consumo de APIs (complementa 2.3/2.4) |
| Documentos asociados | 1.3.Contrato_Datos_OrdenServicio_DuocUC.md, 1.4.Contrato_Operativo_OrdenServicio_DuocUC.md |

### Lista de Distribución

| De | Fecha | Email |
| --- | --- | --- |
| Pablo Moscoso (Docente) | 15/09/2026 | pablo.moscoso@profesor.duoc.cl |

| Para | Acción | Fecha Comprometida | Email |
| --- | --- | --- | --- |
| `<ENCARGADO_DE_LINEA>` | Aprobación | `<FECHA_COMPROMETIDA>` | `<EMAIL_ENCARGADO_DE_LINEA>` |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 15/09/2026 | Pablo Moscoso | Versión inicial |

---

## 2. Propósito y Contexto de Negocio

Este documento describe, en términos de negocio, el propósito y alcance funcional del API demo de Orden de Servicio: por qué existe? quién lo usa? y qué problema resuelve? No repite el detalle técnico ya documentado en el Contrato de Datos y el Contrato Operativo y de Protocolo  este documento se ubica un nivel por encima de ambos y los referencia a lo largo del texto.

El sistema permite registrar, dar seguimiento y cerrar una solicitud de servicio (Orden de Servicio) a lo largo de su ciclo de vida  desde su recepción hasta su cumplimiento o cancelación  replicando, en una versión simplificada con fines educativos, el tipo de interacción que resuelve un sistema real de Service Order Management (SOM) dentro de un proveedor de telecomunicaciones.

Sirve como material de apoyo en el curso CUY6142 para que el estudiante observe el funcionamiento de una API tanto desde el lado que expone el servicio (servidor) como desde el lado que lo consume (cliente, vía Postman o `curl`)  complementando las Actividades 2.3 y 2.4, centradas únicamente en el consumo de APIs ya existentes.

---

## 3. Actores

| Actor | Naturaleza | Rol |
| --- | --- | --- |
| Sistema Cliente | Automatizado (negocio) | Sistema externo  típicamente un CRM o un canal de venta  que emite órdenes de servicio de forma programática. Es el actor principal en la operación normal de un SOM en producción. |
| Actor de Soporte | Manual (negocio, real) | Personal técnico que interactúa directamente con el API mediante herramientas como Postman o `curl` para tareas de soporte: conciliación de órdenes, validación de estado, resolución de incidentes operativos. No es una simplificación pedagógica  refleja un patrón real de operación. |
| Estudiante / Docente | Pedagógico (curso) | En este ejercicio, asume el rol del Actor de Soporte, interactuando directamente con el API vía Postman o `curl`  replicando el mismo flujo de trabajo de un Actor de Soporte real, no uno inventado para la clase. |

El Sistema Cliente no se implementa en este ejercicio: el estudiante lo reemplaza manualmente al crear órdenes directamente, asumiendo ese rol además del de Actor de Soporte según el caso de uso.

---

## 4. Definiciones y Abreviaciones

| Abreviación | Descripción |
| --- | --- |
| API | Application Programming Interface |
| SOM | Service Order Management |
| eTOM | enhanced Telecom Operations Map  marco de procesos de negocio de TM Forum |
| TMF641 | Service Ordering Management  API abierto de TM Forum |
| REST | Representational State Transfer |
| JSON | JavaScript Object Notation |
| ICD | Interface Control Document  equivalente de industria de las Fichas de Contrato de este curso |

---

## 5. Casos de Uso

| Escenario | Secuencia de llamadas al API | Sección de referencia |
| --- | --- | --- |
| Alta de una orden de servicio nueva | Sistema Cliente: `POST /ordenes` | Contrato Operativo, Sección 5 |
| Seguimiento del avance de una orden | Actor de Soporte: `GET /ordenes/{id}` | Contrato Operativo, Sección 5 |
| Actualización de los datos de una orden en curso | Actor de Soporte: `PUT /ordenes/{id}` | Contrato Operativo, Sección 5 |
| Avance de una orden por las etapas de cumplimiento | Actor de Soporte: `PATCH /ordenes/{id}` (`RECIBIDA` → `EN_PROGRESO` → `COMPLETADA`) | Contrato Operativo, Sección 5; Contrato de Datos, Sección 5 |
| Cancelación de una orden en curso | Actor de Soporte: `DELETE /ordenes/{id}` | Contrato Operativo, Sección 5 |
| Intento de conciliar o corregir una orden ya cerrada | Actor de Soporte: `PUT` o `DELETE /ordenes/{id}` sobre una orden en `COMPLETADA` o `CANCELADA` → rechazada | Contrato Operativo, Sección 7 (código `409`) |

El último escenario solo tiene sentido desde el Actor de Soporte, no desde el Sistema Cliente: ilustra por qué existe la restricción de estado terminal, no solo que existe.

---

## 6. Reglas de Negocio

El ciclo de vida de una Orden de Servicio sigue cuatro estados. Se origina en `RECIBIDA` al momento de su creación; avanza a `EN_PROGRESO` cuando comienza su cumplimiento; concluye en `COMPLETADA` cuando el servicio ha sido entregado, o en `CANCELADA` si el cliente o el proceso interno determinan que no debe continuar.

Una orden solo puede cancelarse mientras está `RECIBIDA` o `EN_PROGRESO`. Una vez `COMPLETADA` o `CANCELADA`, se considera cerrada: ningún actor, incluido el Actor de Soporte, puede modificarla ni revertir su estado  esta restricción preserva la integridad del historial de cumplimiento, tal como ocurre en un sistema real de gestión de órdenes.

El detalle técnico completo de esta máquina de estados, incluida la tabla de transiciones válidas, está documentado en el Contrato de Datos, Sección 5.

---

## 7. Relación con el Proceso de Negocio

Este sistema simplifica, con fines educativos, el proceso eTOM **Order Handling** (Process Identifier 1.1.1.5), dentro del área de Customer Relationship Management / Operations del marco eTOM de TM Forum. Order Handling es responsable de aceptar y emitir órdenes, determinar su factibilidad, y dar seguimiento a su estado hasta notificar su cumplimiento al cliente  exactamente el alcance que cubre este API.

El sistema se alinea conceptualmente, sin pretender conformidad ni certificación, con el API abierto **TMF641 (Service Ordering Management)** de TM Forum, la versión estandarizada de industria de este mismo proceso.

Quedan explícitamente fuera del alcance otros procesos eTOM que un sistema SOM real suele integrar:

- **Assurance**  gestión de incidentes y tickets de soporte sobre un servicio ya activo.
- **Billing**  facturación del servicio.

Este API cubre únicamente Order Handling, dentro del proceso más amplio de Fulfillment.

---

## 8. Fuera de Alcance Funcional y Dependencias

### Fuera de Alcance Funcional

- Facturación o cálculo de costos asociados a la orden.
- Gestión de incidentes o tickets de soporte sobre un servicio ya activo (Assurance).
- Integración con sistemas externos reales (CRM, inventario, agendamiento de visitas técnicas)  el Sistema Cliente se simula manualmente en este ejercicio.
- Gestión de usuarios o permisos diferenciados por actor  toda la autenticación usa una única credencial compartida (Contrato Operativo, Sección 4).

### Dependencias

- Prerrequisito del curso, CUY5132, cumplido.
- Actividades 2.3 y 2.4 (Fundamentos y Consumo de APIs) cursadas previamente  este ejercicio asume manejo previo de Postman/`curl` como cliente.
- Contrato de Datos y Contrato Operativo y de Protocolo (Orden de Servicio) vigentes y aprobados  este documento no tiene sentido de forma aislada.

---

## 9. Lista de Referencias

| Documento | Descripción |
| --- | --- |
| `Contrato_Datos_OrdenServicio_DuocUC.md` | Contrato de Datos (schema) del recurso Orden de Servicio |
| `Contrato_Operativo_OrdenServicio_DuocUC.md` | Contrato Operativo y de Protocolo del API Orden de Servicio |
| `som_api_demo.py` | Implementación de referencia del API |
| `Estandar_Documentacion_API_CUY6142.md` | Estándar de documentación aplicado a este conjunto de documentos (uso interno del docente) |
| TM Forum  Business Process Framework (eTOM) | Marco de procesos de negocio de referencia de industria  tmforum.org |
| TM Forum  TMF641 (Service Ordering Management) | API abierto de referencia para gestión de órdenes de servicio  tmforum.org |

---

## 10. Control de Versiones de la Especificación

Un cambio que solo actualiza contexto de negocio, actores o casos de uso, sin afectar las Fichas de Contrato: cambio menor. Un cambio que requiere modificar el Contrato de Datos o el Contrato Operativo (ej. un nuevo actor con permisos distintos, o un nuevo escenario que necesita un endpoint nuevo): cambio mayor, coordinado con ambas fichas.

Esta especificación documenta la versión **1.0** del sistema.

---

## 11. Aprobación

Esta sección resume la aceptación formal de la presente Especificación Funcional.

| Nombre | `<ENCARGADO_DE_LINEA>` |
| --- | --- |
| Cargo | Encargado de Línea, Escuela de Informática y Telecomunicaciones |
| Fecha | `<FECHA_APROBACION>` |
| Firma | ____________________________ |

---

*Documento de referencia  no es un procedimiento (MOP). Se actualiza cuando cambia el propósito, los actores o los casos de uso del sistema; los cambios técnicos se documentan en las Fichas de Contrato asociadas.*
