<div style="background-color:#307FE2; padding: 28px 36px; margin-bottom: 4px;">
  <img src="[ruta al logo]" alt="Duoc UC" style="height:42px;" />
</div>
<div style="background-color:#1A1A1A; padding: 4px 36px 20px 36px; margin-bottom: 28px;">
  <h1 style="font-family: Merriweather, Georgia, serif; color:#FFFFFF; margin: 12px 0 4px 0;">Contrato Operativo y de Protocolo — Orden de Servicio</h1>
  <p style="font-family: Lato, Calibri, sans-serif; color:#8BB8E8; margin: 0; font-size: 0.95em;">CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana</p>
</div>

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Contrato Operativo y de Protocolo — Orden de Servicio (API Demo eTOM/SOM) |
| Versión | 2.0 |
| Fecha | 05/10/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | EA2 — Fundamentos y Consumo de APIs (2.3 / 2.4); base de la actividad formativa 2.4.2 |
| Documento asociado | Contrato de Datos — Orden de Servicio (versión 2.0) |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 14/09/2026 | Pablo Moscoso | Versión inicial |
| 1.1 | 14/09/2026 | Pablo Moscoso | Validación de conformidad contra `Estandar_Documentacion_API_CUY6142.md` (Sección 3, checklist de Ficha de Contrato); agregada Sección 10 "Control de Versiones del Contrato", ausente respecto a la Sección 1.5 del estándar — Glosario renumerado de 10 a 11 |
| 1.2 | 14/09/2026 | Pablo Moscoso | Agregado método `PUT /ordenes/{id}` (reemplazo completo de campos editables) a la Sección 5, con nota explicativa de la diferencia con `PATCH`; actualizadas Secciones 7 (códigos de estado) y 8 (idempotencia) en consecuencia |
| 1.3 | 17/09/2026 | Pablo Moscoso | Sección 4 rediseñada: autenticación por mapa de dos claves por canal (`GUI`, `CRM`). Agregada Sección 6, Webhooks. Agregados endpoints `POST /webhooks` y `GET /webhooks/fallos`. Renumeradas Secciones 6 a 11 → 7 a 12 |
| 2.0 | 05/10/2026 | Pablo Moscoso | Cambio mayor, ruta base `/api/v2`. Sección 3: perfil de instancia AWS del estudiante y persistencia en volumen. Sección 4: login con autenticación básica (`loginViaBasic`) y tokens de sesión; credencial por header `X-API-KEY` o parámetro `key`. Sección 5: endpoints de trazabilidad, suscripciones y ofertas; parámetros de consulta (filtros, `sortBy`, `order`, `page`, `size`, `includeOferta`, `idioma`, `q`, `limit`); `PATCH` ampliado a `descripcion`; documentación navegable OpenAPI/Swagger. Sección 6: payload del webhook con `tipo_orden`, `com_id` y `subscription_id`. Sección 8: correspondencia entre reglas del Contrato de Datos (RV, RN) y códigos HTTP. Sección 9: serialización de la ejecución y `com_id` como clave de idempotencia. Sección 10: persistencia sale de las exclusiones |

---

## 2. Propósito y Alcance

Este documento define **cómo** un cliente interactúa con el servicio: transporte, autenticación, endpoints, parámetros de consulta, formato de mensajes y códigos de estado. La estructura de los datos que viajan en cada mensaje (Orden de Servicio, Suscripción, Oferta y Trazabilidad), sus reglas de validación (RV) y sus reglas de negocio (RN) se definen en el **Contrato de Datos — Orden de Servicio**; este documento no repite esas definiciones, solo las referencia y asigna a cada regla su código de estado HTTP (Sección 8).

El servicio simplifica el proceso eTOM **Order Handling** (Process Identifier 1.1.1.5), inspirado en el tipo de interacción cliente-servidor de un sistema real de Service Order Management (SOM), y alineado conceptualmente con los APIs abiertos TM Forum **TMF641**, **TMF638** y **TMF620** (ver Contrato de Datos, Sección 2), sin pretender conformidad ni certificación con esos estándares.

---

## 3. Modos de Despliegue y Host

Todos los perfiles usan el mismo puerto y el mismo contrato; solo cambia el host.

| Perfil | Host | Puerto | Cuándo se usa |
| --- | --- | --- | --- |
| Instancia del estudiante | `<IP_PUBLICA_INSTANCIA>` | `8081` | Perfil principal. Cada estudiante despliega el servicio en su propia instancia EC2 de AWS Academy y lo consume desde su equipo (Postman, scripts Python). Requiere la regla de entrada TCP `8081` en el grupo de seguridad de la instancia. El valor real es la IP pública de la instancia, que cambia en cada inicio del Learner Lab. |
| Local | `localhost` (o `127.0.0.1`) | `8081` | Pruebas desde la misma máquina donde corre el servicio (por ejemplo, desde la sesión SSH de la instancia). |
| Demo docente | `<IP_DOCENTE>` | `8081` | Demostración en clase desde el equipo o la instancia del docente. El valor real se anuncia al inicio de la sesión. |
| Entre contenedores | `som-api` | `8081` | Otro contenedor conectado a la misma red Docker definida por el usuario (por ejemplo, `crm-som` en la red `som-network`). |

**Base URL:** `http://<HOST>:8081/api/v2`

La versión 2.0 del servicio expone solo la ruta base `/api/v2`. La ruta `/api/v1` no se expone (Sección 11).

**Transporte:** HTTP sin TLS. Es una limitación declarada, no una omisión: evita que cada estudiante deba generar y confiar un certificado en su instancia, lo que introduciría gestión de PKI ajena al objetivo del ejercicio. Consecuencia explícita: las credenciales (Sección 4) viajan en texto plano. Aceptable en el contexto de este ejercicio, no aceptable como patrón para un despliegue en producción.

**Persistencia.** Las órdenes, las suscripciones y los contadores correlativos de `subscription_id` se guardan en un archivo JSON. La ruta del archivo se define con la variable de entorno `SOM_DATA_FILE`; por defecto es `data/som_data.json`, relativa al directorio de trabajo del proceso (`/app/data/som_data.json` dentro del contenedor). En el despliegue con Docker, el directorio `/app/data` se monta como volumen: los datos sobreviven al reinicio o recreación del contenedor y se pierden solo si se elimina el volumen. No se persisten los tokens de sesión (Sección 4), el webhook registrado ni el historial de entregas fallidas (Sección 6), que se pierden al reiniciar el proceso.

**Fuera del alcance de este contrato:** configuración del grupo de seguridad, firewall del sistema operativo y red del entorno de ejecución. Son responsabilidad operativa de quien despliega el servicio, documentada en el MOP de despliegue correspondiente.

---

## 4. Autenticación

### 4.1 Credenciales de acceso a los endpoints

| Aspecto | Definición |
| --- | --- |
| Mecanismo | Header HTTP `X-API-KEY`, o parámetro de consulta `key` en la URL |
| Precedencia | Si la solicitud incluye ambos, se usa el header y se ignora el parámetro |
| Credenciales válidas | Un token de sesión obtenido con `loginViaBasic` (Sección 4.2), o una clave fija de canal (Sección 4.3) |
| Endpoints que la exigen | Todos, excepto `loginViaBasic` y la documentación navegable (Sección 5.4) |
| Momento de validación | Antes de procesar el cuerpo de la solicitud, es decir, antes de aplicar el Contrato de Datos |
| Falla | Credencial ausente o no válida → `401` con código `NO_AUTORIZADO` (Sección 8) |

Los nombres de header HTTP no distinguen mayúsculas de minúsculas: `X-API-KEY` y el `X-API-Key` de la versión 1.x son el mismo header.

### 4.2 Login con autenticación básica (`loginViaBasic`)

Flujo equivalente al de la API de biblioteca usada en la actividad 2.3.2: el cliente se autentica con usuario y contraseña y recibe un token que luego envía en `X-API-KEY`.

| Aspecto | Definición |
| --- | --- |
| Endpoint | `POST /api/v2/loginViaBasic`, sin cuerpo |
| Mecanismo | Header HTTP `Authorization: Basic <base64(usuario:contraseña)>` (autenticación básica HTTP) |
| Usuarios | `gui` (canal `GUI`) y `crm` (canal `CRM`), ambos con contraseña `Cuy6142!` |
| Respuesta exitosa | `200` con cuerpo `{"token": "<usuario>|<cadena aleatoria>"}` |
| Token | Distinto en cada login. Varios tokens del mismo usuario pueden estar vigentes a la vez. Hereda el canal del usuario que lo obtuvo |
| Vigencia | Hasta que se reinicia el proceso del servicio. No hay expiración por tiempo ni cierre de sesión |
| Falla | Header `Authorization` ausente, mal formado, o usuario y contraseña incorrectos → `401` con código `CREDENCIALES_INVALIDAS` y header `WWW-Authenticate: Basic realm="SOM"` |

Ejemplo de respuesta:

```json
{
  "token": "gui|q8Zt3LxV0mNcR7yPk2sWfH9bJ4eTu6aGdQ1vXiO5lEw"
}
```

El token contiene el carácter `|`. En la línea de comandos, toda URL o header que lo incluya debe ir entre comillas simples; de lo contrario, la shell interpreta `|` como una tubería. Las librerías HTTP (Postman, `requests`) lo codifican automáticamente cuando se usa como parámetro `key`.

### 4.3 Claves fijas de canal

| Aspecto | Definición |
| --- | --- |
| Propósito | Integración entre sistemas, donde no hay un usuario que inicie sesión (por ejemplo, `crm-som`) |
| Canales | `GUI` y `CRM`, una clave por canal |
| Valor documental | `<API_KEY_CUY6142_GUI>` y `<API_KEY_CUY6142_CRM>`. Los valores reales vienen en el código del servicio y se indican en el MOP de despliegue |
| Continuidad | Son las mismas claves de la versión 1.3 |

### 4.4 Canal de origen

Toda solicitud autenticada tiene un **canal de origen** (`canal_origen`): el canal de la clave fija usada, o el canal del usuario que obtuvo el token. Se usa en el registro de log y en el payload de los webhooks (Sección 6). El canal no es un valor que el cliente declare en el cuerpo de su solicitud: se deriva de la credencial con que se autenticó, lo que lo hace fiable como dato de auditoría.

Distinción conceptual relevante para la clase: la credencial valida **quién llama** (nivel de protocolo); `cliente_id` en el cuerpo de la orden identifica **a nombre de quién se realiza la operación** (nivel de negocio, definido en el Contrato de Datos). Son conceptos independientes.

---

## 5. Endpoints y Métodos

### 5.1 Tabla de endpoints

Rutas relativas a la base URL `/api/v2`.

| Método | Ruta | Acción | Éxito | Errores posibles |
| --- | --- | --- | --- | --- |
| POST | `/loginViaBasic` | Obtener un token de sesión | `200 OK` | `401` |
| POST | `/ordenes` | Crear orden (cualquier tipo) | `201 Created` | `400`, `401`, `404`, `409`, `422` |
| GET | `/ordenes` | Listar órdenes, con filtros, orden y paginación | `200 OK` | `400`, `401` |
| GET | `/ordenes/{id}` | Consultar una orden | `200 OK` | `400`, `401`, `404` |
| PUT | `/ordenes/{id}` | Reemplazo completo de los campos editables | `200 OK` | `400`, `401`, `404`, `409`, `422` |
| PATCH | `/ordenes/{id}` | Actualización parcial de `descripcion` y/o transición de `estado` | `200 OK` | `400`, `401`, `404`, `409`, `422` |
| DELETE | `/ordenes/{id}` | Cancelar orden | `200 OK` | `401`, `404`, `409` |
| GET | `/ordenes/{id}/trazabilidad` | Consultar la trazabilidad de una orden | `200 OK` | `400`, `401`, `404` |
| GET | `/suscripciones` | Listar suscripciones, con filtros y paginación | `200 OK` | `400`, `401` |
| GET | `/suscripciones/{subscription_id}` | Consultar una suscripción | `200 OK` | `401`, `404` |
| GET | `/ofertas` | Listar o buscar ofertas del catálogo | `200 OK` | `400`, `401` |
| GET | `/ofertas/{offer_id}` | Consultar una oferta | `200 OK` | `401`, `404` |
| POST | `/webhooks` | Registrar receptor de notificaciones asíncronas | `201 Created` | `400`, `401`, `422` |
| GET | `/webhooks/fallos` | Consultar intentos de notificación fallidos | `200 OK` | `401` |
| GET | `/docs` | Documentación navegable (Swagger UI) | `200 OK` | Ninguno (sin autenticación) |
| GET | `/openapi.json` | Especificación OpenAPI 3.0 del servicio | `200 OK` | Ninguno (sin autenticación) |

**Respuestas.** La creación, la consulta, el reemplazo, la actualización parcial y la cancelación de una orden devuelven su representación completa (Contrato de Datos, Sección 3.1). Los listados devuelven un arreglo JSON de representaciones completas; un listado sin resultados devuelve `200` con un arreglo vacío. `PATCH` y `DELETE` exitosos que cambian `estado` pueden disparar además una notificación asíncrona (Sección 6).

### 5.2 Parámetros de consulta

Un parámetro desconocido se ignora. Un parámetro conocido con un valor inválido responde `400` con código `PARAMETRO_INVALIDO`. Los valores booleanos se escriben `true` o `false`.

**`GET /ordenes`**

| Parámetro | Valores | Default | Efecto |
| --- | --- | --- | --- |
| `cliente_id`, `subscription_id`, `com_id`, `tipo_servicio`, `tipo_orden` | Valor exacto del campo | Sin filtro | Filtra por igualdad |
| `estado` | Uno o más estados de orden; se repite el parámetro para indicar varios (`estado=RECIBIDA&estado=EN_PROGRESO`) | Sin filtro | Devuelve las órdenes en cualquiera de los estados indicados |
| `sortBy` | `fecha_creacion`, `com_id`, `cliente_id`, `subscription_id`, `tipo_orden`, `tipo_servicio`, `estado`, `prioridad` | `fecha_creacion` | Campo de ordenamiento. Empates: por `fecha_creacion` y luego por `id` |
| `order` | `asc`, `desc` | `asc` | Sentido del ordenamiento |
| `page` | Entero mayor o igual a 1 | `1` | Página solicitada. Una página posterior a la última devuelve un arreglo vacío |
| `size` | Entero entre 1 y 100 | `20` | Cantidad de órdenes por página |
| `includeOferta` | `true`, `false` | `false` | Agrega a cada orden el campo `oferta` (representación expandida, Contrato de Datos, Sección 3.1) |

Los filtros distintos se combinan entre sí (todos deben cumplirse). La respuesta incluye el header `X-Total-Count` con la cantidad total de órdenes que cumplen los filtros, antes de paginar. Para obtener la totalidad de un listado se recorren las páginas hasta completar ese total.

**`GET /ordenes/{id}`**

| Parámetro | Valores | Default | Efecto |
| --- | --- | --- | --- |
| `includeOferta` | `true`, `false` | `false` | Igual que en el listado |

**`GET /ordenes/{id}/trazabilidad`**

| Parámetro | Valores | Default | Efecto |
| --- | --- | --- | --- |
| `idioma` | `es`, `en` | `en` | Idioma de los textos de los pasos de trabajo (Contrato de Datos, Sección 4.4) |

**`GET /suscripciones`**

| Parámetro | Valores | Default | Efecto |
| --- | --- | --- | --- |
| `cliente_id`, `tipo_servicio` | Valor exacto del campo | Sin filtro | Filtra por igualdad |
| `estado` | Uno o más estados de suscripción, repitiendo el parámetro | Sin filtro | Igual que en el listado de órdenes |
| `page`, `size` | Igual que en el listado de órdenes | `1`, `20` | Paginación |

Ordenamiento fijo por `subscription_id` ascendente. La respuesta incluye el header `X-Total-Count`.

**`GET /ofertas`**

| Parámetro | Valores | Default | Efecto |
| --- | --- | --- | --- |
| `q` | Texto libre | Sin filtro | Devuelve las ofertas cuyo `nombre` contiene el texto, sin distinguir mayúsculas de minúsculas |
| `tipo_servicio` | Valor exacto | Sin filtro | Filtra por servicio |
| `limit` | Entero mayor o igual a 1 | Sin límite | Cantidad máxima de ofertas a devolver |

Ordenamiento fijo por `offer_id` ascendente.

### 5.3 Diferencia entre `PUT` y `PATCH` en este contrato

- **`PUT`** reemplaza **toda** la representación editable de la orden: `prioridad` y `descripcion` son obligatorios en el cuerpo, incluso si no cambian (Contrato de Datos, RV-07). Los campos inmutables pueden incluirse, pero deben coincidir con sus valores vigentes (RN-13); los de solo lectura se ignoran (RV-09). `PUT` nunca modifica `estado` y no dispara webhook. Es **idempotente**.
- **`PATCH`** modifica **parcialmente** la orden. Su cuerpo contiene `descripcion`, `estado`, o ambos, y ningún otro campo (RV-08). Si incluye `estado`, solicita una transición según la máquina de estados (Contrato de Datos, Sección 5.1).
- Un `PATCH` con ambos campos se aplica completo o no se aplica: si la transición de `estado` es rechazada, `descripcion` tampoco cambia.
- Solo un `PATCH` que cambia `estado` dispara webhook. Un `PATCH` que solo modifica `descripcion` no lo dispara.
- Ninguno de los dos se acepta sobre una orden en estado terminal (RN-12).

### 5.4 Documentación navegable

| Ruta | Contenido |
| --- | --- |
| `/api/v2/docs` | Interfaz Swagger UI, equivalente a la página de documentación de la API de biblioteca de la actividad 2.3.2. Permite explorar los endpoints, autorizar con `X-API-KEY` o con autenticación básica, y ejecutar solicitudes de prueba |
| `/api/v2/openapi.json` | Especificación OpenAPI 3.0 del servicio, en formato JSON |

Ninguna de las dos rutas exige autenticación. La interfaz Swagger UI se carga desde una red de distribución de contenido pública: el navegador que la abre necesita acceso a internet.

### 5.5 Ejemplos de uso

Los ejemplos usan `<HOST>` (Sección 3), `<TOKEN>` (el valor obtenido en el primer ejemplo) y `<ID_ORDEN>` (el `id` devuelto por la creación). Cada flujo es reproducible en Postman: autenticación básica en la pestaña Authorization (tipo Basic Auth) para el login; header `X-API-KEY` para el resto; cuerpo JSON en Body → raw → JSON.

**Obtener un token:**
```
curl -X POST 'http://<HOST>:8081/api/v2/loginViaBasic' \
  -u 'gui:Cuy6142!'
```

**Buscar una oferta, con la credencial en la URL:**
```
curl 'http://<HOST>:8081/api/v2/ofertas?q=fibra&limit=1&key=<TOKEN>'
```

**Crear un `ALTA`:**
```
curl -X POST 'http://<HOST>:8081/api/v2/ordenes' \
  -H 'X-API-KEY: <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"ALTA","com_id":"1000001","cliente_id":"CL-10457","tipo_servicio":"INTERNET","offer_id":"200102"}'
```

**Transicionar una orden a `EN_PROGRESO`:**
```
curl -X PATCH 'http://<HOST>:8081/api/v2/ordenes/<ID_ORDEN>' \
  -H 'X-API-KEY: <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"estado":"EN_PROGRESO"}'
```

**Actualizar solo la descripción (`PATCH`):**
```
curl -X PATCH 'http://<HOST>:8081/api/v2/ordenes/<ID_ORDEN>' \
  -H 'X-API-KEY: <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"descripcion":"Cliente solicita visita en horario AM"}'
```

**Reemplazar los campos editables (`PUT`):**
```
curl -X PUT 'http://<HOST>:8081/api/v2/ordenes/<ID_ORDEN>' \
  -H 'X-API-KEY: <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"prioridad":"ALTA","descripcion":"Cliente solicita visita en horario AM"}'
```

**Crear una `RELOCALIZACION`:**
```
curl -X POST 'http://<HOST>:8081/api/v2/ordenes' \
  -H 'X-API-KEY: <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"RELOCALIZACION","com_id":"1000002","cliente_id":"CL-10457","subscription_id":"20000001","punto_actual":{"x":2.5,"y":1.75,"referencia":"Living"},"punto_destino":{"x":6.125,"y":4.5,"referencia":"Dormitorio 2"}}'
```

**Consultar la trazabilidad en español:**
```
curl 'http://<HOST>:8081/api/v2/ordenes/<ID_ORDEN>/trazabilidad?idioma=es' \
  -H 'X-API-KEY: <TOKEN>'
```

**Listar órdenes ordenadas por suscripción, con la oferta expandida, mostrando los headers de respuesta (`-i`):**
```
curl -i 'http://<HOST>:8081/api/v2/ordenes?sortBy=subscription_id&includeOferta=true&page=1&size=20' \
  -H 'X-API-KEY: <TOKEN>'
```

**Listar las órdenes pendientes de ejecución (filtro multivalor):**
```
curl 'http://<HOST>:8081/api/v2/ordenes?estado=RECIBIDA&estado=EN_PROGRESO' \
  -H 'X-API-KEY: <TOKEN>'
```

**Listar las suscripciones activas de un cliente:**
```
curl 'http://<HOST>:8081/api/v2/suscripciones?cliente_id=CL-10457&estado=ACTIVA' \
  -H 'X-API-KEY: <TOKEN>'
```

**Cancelar una orden:**
```
curl -X DELETE 'http://<HOST>:8081/api/v2/ordenes/<ID_ORDEN>' \
  -H 'X-API-KEY: <TOKEN>'
```

---

## 6. Webhooks — Notificaciones Asíncronas de Cambio de Estado

### 6.1 Propósito y alcance

Esta sección define el mecanismo por el cual el servicio informa a un receptor externo, por su propia iniciativa, que una orden cambió de estado, sin que el receptor deba consultar repetidamente (`polling`). Es el mismo patrón que usa Cisco Webex para notificar eventos a una integración externa: el servidor llama al cliente, invirtiendo la dirección habitual de la comunicación.

No sustituye las respuestas síncronas de la Sección 5: es un segundo aviso, posterior, sobre un cambio que ya ocurrió.

### 6.2 Registro del webhook

| Aspecto | Definición |
| --- | --- |
| Endpoint | `POST /api/v2/webhooks` |
| Autenticación | Igual que el resto de los endpoints (Sección 4.1) |
| Cuerpo de la solicitud | `{"url": "<URL del receptor>"}` |
| Alcance | Un único webhook activo por servicio: registrar uno nuevo reemplaza al anterior |
| Persistencia | En memoria; se pierde al reiniciar el proceso (Sección 3) |
| Validación | `url` es obligatorio y debe ser un string no vacío (`422`). No se valida que la URL sea alcanzable en el registro, solo en el disparo (Sección 6.4) |

**Registrar un receptor:**
```
curl -X POST 'http://<HOST>:8081/api/v2/webhooks' \
  -H 'X-API-KEY: <API_KEY_CUY6142_CRM>' \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://crm-som:8082/webhooks/ordenes"}'
```

### 6.3 Condiciones de disparo

El servicio dispara una notificación hacia el webhook registrado únicamente cuando:

- Un `PATCH` que incluye `estado` se completa con éxito (`200`).
- Un `DELETE` se completa con éxito (`200`).

No se dispara en creación, consulta, reemplazo (`PUT`) ni en un `PATCH` que solo modifica `descripcion`: ninguna de esas operaciones cambia `estado`. Un intento fallido de `PATCH` o `DELETE` no dispara webhook. Los cambios de estado de una suscripción (Contrato de Datos, Sección 5.3) no generan un evento propio: se deducen del evento de la orden que los produjo.

### 6.4 Modelo de entrega

La notificación se envía en un hilo de ejecución separado del que atiende la solicitud original, con un timeout de 3 segundos y **sin reintentos automáticos**. El llamador original recibe su respuesta sin esperar el resultado de la entrega: la respuesta síncrona confirma que el estado cambió; la entrega del webhook, si ocurre, llega después y por un canal distinto. La Sección 6.7 documenta el mecanismo de conciliación que compensa la ausencia de reintentos.

**Nota para quien implemente el receptor:** si el receptor también llama de vuelta a este servicio, su servidor debe poder atender solicitudes entrantes de forma concurrente con sus propias solicitudes salientes; de lo contrario, puede quedar interbloqueado. Es responsabilidad del receptor, fuera del alcance de este contrato.

### 6.5 Payload del evento

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `evento` | string | Tipo de evento. Valor fijo actual: `cambio_estado` |
| `orden_id` | string (UUID) | `id` de la orden afectada |
| `tipo_orden` | enum | Tipo de la orden afectada |
| `com_id` | string | `com_id` de la orden afectada |
| `subscription_id` | string | Suscripción de la orden afectada |
| `estado_anterior` | enum | Estado antes de la operación |
| `estado_nuevo` | enum | Estado después de la operación |
| `operacion` | enum (`PATCH`, `DELETE`) | Operación que disparó el evento |
| `canal_origen` | enum (`CRM`, `GUI`) | Canal que ejecutó la operación (Sección 4.4) |
| `fecha_evento` | string (ISO 8601) | Momento en que se disparó la notificación |

**Ejemplo de payload saliente:**
```json
{
  "evento": "cambio_estado",
  "orden_id": "3f2a9e1c-8b4d-4a6e-9c2f-1d7e5b6a0f33",
  "tipo_orden": "ALTA",
  "com_id": "1000001",
  "subscription_id": "20000001",
  "estado_anterior": "EN_PROGRESO",
  "estado_nuevo": "COMPLETADA",
  "operacion": "PATCH",
  "canal_origen": "GUI",
  "fecha_evento": "2026-10-05T13:30:00Z"
}
```

El payload no envía la representación completa de la orden. El receptor que necesite más detalle consulta `GET /ordenes/{orden_id}` o `GET /suscripciones/{subscription_id}`.

### 6.6 Autenticación saliente

| Aspecto | Definición |
| --- | --- |
| Mecanismo | Header HTTP `X-Webhook-Secret` en la solicitud saliente hacia el receptor |
| Alcance | Único y fijo, compartido por todo el curso |
| Valor documental | `<WEBHOOK_SECRET_CUY6142>` |
| Propósito | El receptor puede validar que el callback entrante proviene de este servicio |

Limitación declarada: es una comparación directa de secreto compartido, no una firma criptográfica (HMAC) del cuerpo, como la que usa Webex con su header `X-Spark-Signature`. La firma HMAC queda fuera de alcance de esta versión.

### 6.7 Manejo de fallos y conciliación

Si la entrega falla (timeout, conexión rechazada o código de respuesta de error del receptor), el servicio registra el intento en el log del proceso y en un registro consultable:

```
curl 'http://<HOST>:8081/api/v2/webhooks/fallos' \
  -H 'X-API-KEY: <API_KEY_CUY6142_CRM>'
```

| Campo | Descripción |
| --- | --- |
| `orden_id` | Orden afectada por el cambio no notificado |
| `operacion` | `PATCH` o `DELETE` |
| `canal_origen` | Canal que ejecutó la operación original |
| `url_destino` | URL registrada en el momento del intento |
| `motivo` | Descripción del fallo |
| `fecha_intento` | Momento del intento fallido |

Este endpoint es el mecanismo de conciliación: el receptor, o quien opera el servicio, lo consulta y reconcilia su estado local contra `GET /ordenes/{id}`.

Toda respuesta de `PATCH` o `DELETE` que dispare un intento de notificación incluye el campo `notificacion_webhook` con valor `"pendiente"`. Es un campo de protocolo, ajeno a la representación del recurso definida en el Contrato de Datos: avisa que se intentará la notificación, no confirma su entrega.

### 6.8 Exclusiones declaradas de esta sección

- Reintentos automáticos de entrega (Sección 6.4).
- Firma criptográfica (HMAC) del payload saliente (Sección 6.6).
- Múltiples suscriptores simultáneos (Sección 6.2).
- Persistencia del webhook registrado y del historial de fallos (Sección 3).
- Deduplicación de eventos del lado del servidor: `orden_id` junto con `fecha_evento` permiten construirla en el receptor.

---

## 7. Formato de Mensajes

- `Content-Type: application/json` obligatorio en toda solicitud con cuerpo (`POST /ordenes`, `PUT`, `PATCH`, `POST /webhooks`). Sin ese header, el cuerpo se trata como JSON inválido (`400`).
- Codificación: UTF-8.
- Formato de error estandarizado, idéntico en todos los endpoints:

```json
{
  "error": {
    "codigo": "SUSCRIPCION_NO_ACTIVA",
    "mensaje": "La suscripcion 20000001 no esta ACTIVA (estado actual: BAJA)"
  }
}
```

`codigo` es estable y apto para que un programa lo evalúe; `mensaje` es descriptivo y puede variar.

---

## 8. Códigos de Estado HTTP del Contrato

### 8.1 Códigos

| Código | Significado en este contrato | Cuándo se produce |
| --- | --- | --- |
| `200 OK` | Operación exitosa | Login, consultas, `PUT`, `PATCH`, `DELETE` exitosos |
| `201 Created` | Recurso creado | Creación de una orden o registro de un webhook |
| `400 Bad Request` | Solicitud mal formada | Cuerpo que no es JSON válido, o parámetro de consulta con valor inválido |
| `401 Unauthorized` | Falla de autenticación | Credencial ausente o no válida, o login con credenciales incorrectas |
| `404 Not Found` | Recurso inexistente | El recurso de la ruta no existe, o el cuerpo referencia una oferta o suscripción que no existe |
| `409 Conflict` | Rechazo por el estado actual de los datos | Violación de una regla de negocio que depende del estado almacenado (Sección 8.2) |
| `422 Unprocessable Entity` | Contenido inválido | JSON válido que viola una regla de schema, o una regla de negocio sobre la coherencia del propio contenido (Sección 8.2) |
| `500 Internal Server Error` | Fallo no controlado del servidor | Excepción no anticipada (código `ERROR_INTERNO`) |

Las rutas no documentadas y los métodos no soportados en una ruta documentada responden con los códigos propios del framework (`404`, `405`) y no forman parte de este contrato.

### 8.2 Correspondencia entre reglas y códigos

| Situación o regla (Contrato de Datos) | HTTP | `codigo` |
| --- | --- | --- |
| Credencial ausente o no válida (Sección 4.1) | `401` | `NO_AUTORIZADO` |
| Login con credenciales incorrectas (Sección 4.2) | `401` | `CREDENCIALES_INVALIDAS` |
| Cuerpo no es JSON válido o falta `Content-Type` | `400` | `JSON_INVALIDO` |
| Parámetro de consulta con valor inválido (Sección 5.2) | `400` | `PARAMETRO_INVALIDO` |
| Orden de la ruta inexistente | `404` | `ORDEN_NO_ENCONTRADA` |
| Suscripción de la ruta inexistente, o RN-04 | `404` | `SUSCRIPCION_NO_ENCONTRADA` |
| Oferta de la ruta inexistente, o RN-02 | `404` | `OFERTA_NO_ENCONTRADA` |
| RV-01 a RV-08, y registro de webhook sin `url` válida | `422` | `SCHEMA_INVALIDO` |
| RV-09, RV-10 | — | No son errores: los campos se ignoran |
| RN-01 | `409` | `COM_ID_DUPLICADO` |
| RN-03 | `422` | `OFERTA_NO_CORRESPONDE_A_SERVICIO` |
| RN-05 | `409` | `SUSCRIPCION_NO_PERTENECE_A_CLIENTE` |
| RN-06 | `422` | `SERVICIO_NO_CORRESPONDE_A_SUSCRIPCION` |
| RN-07 | `409` | `SUSCRIPCION_NO_ACTIVA` |
| RN-08 | `409` | `OFERTA_SIN_CAMBIO` |
| RN-09 | `422` | `PUNTOS_IDENTICOS` |
| RN-10 | `409` | `ORDEN_EN_CURSO` |
| RN-11 | `409` | `TRANSICION_INVALIDA` |
| RN-12 | `409` | `ORDEN_EN_ESTADO_TERMINAL` |
| RN-13 | `409` | `CAMPO_INMUTABLE` |

Cuando una solicitud viola varias reglas, se informa solo la primera, según este orden de capas: autenticación (`401`), existencia del recurso de la ruta (`404`), formato (`400`), schema (`422`) y reglas de negocio. El orden de evaluación de las reglas de negocio de cada operación se define en el Diseño Funcional.

### 8.3 Criterio de asignación: `400`, `422` y `409`

- **`400`**: la solicitud no se puede interpretar (el cuerpo no es JSON, o un parámetro de la URL tiene un valor sin sentido para ese parámetro).
- **`422`**: la solicitud se interpreta, pero su contenido es incoherente por sí mismo, sin importar qué haya almacenado: falta un campo, un valor está fuera de dominio, la oferta pertenece a otro servicio, los dos puntos son iguales.
- **`409`**: el contenido es coherente, pero choca con el estado actual de los datos almacenados: el `com_id` ya existe, la suscripción no está activa, otra orden está en ejecución, la orden ya terminó.

Una misma solicitud puede ser válida hoy y rechazada con `409` mañana; una rechazada con `422` lo será siempre.

---

## 9. Idempotencia y Concurrencia

- `GET` y `PUT` son idempotentes. Un `PATCH` que solo modifica `descripcion` también lo es.
- Repetir un `PATCH` de `estado` o un `DELETE` ya aplicados no vuelve a cambiar la orden: la segunda llamada responde `409` (`TRANSICION_INVALIDA` u `ORDEN_EN_ESTADO_TERMINAL`) y el estado final es el mismo.
- `POST /ordenes` no es idempotente en sentido estricto, pero `com_id` actúa como **clave de idempotencia**: repetir una creación con el mismo `com_id` responde `409` (`COM_ID_DUPLICADO`) y no crea una segunda orden. Protege contra el doble envío accidental.
- `POST /loginViaBasic` no es idempotente: cada llamada emite un token nuevo.
- `fecha_actualizacion` cambia en cada modificación exitosa aunque el resto de los campos no varíe. Es un efecto esperado.
- **Serialización de la ejecución:** el servicio verifica y aplica de forma atómica las reglas que dependen de otras órdenes (RN-01, RN-10). Dos solicitudes simultáneas no pueden crear dos órdenes con el mismo `com_id`, ni dejar dos órdenes de una misma suscripción en `EN_PROGRESO` (Contrato de Datos, Sección 5.4).
- No hay control de concurrencia optimista (sin versión de recurso ni header `ETag`): si dos clientes modifican la `descripcion` de una misma orden, prevalece la última escritura.

---

## 10. Exclusiones Declaradas del Contrato

- TLS/HTTPS (Sección 3).
- Expiración, revocación y persistencia de los tokens de sesión (Sección 4.2).
- Autenticación individual por estudiante: los usuarios y las claves son por canal, no por persona. Cada estudiante opera su propia instancia del servicio.
- Administración del catálogo de ofertas: es fijo y de solo lectura (Contrato de Datos, Sección 3.4).
- Límite de solicitudes por cliente (rate limiting).
- Control de concurrencia optimista (Sección 9).
- Configuración de red del entorno de ejecución (Sección 3).
- Reintentos, firma HMAC, múltiples suscriptores y persistencia de webhooks (Sección 6.8).

---

## 11. Control de Versiones del Contrato

- Agregar un endpoint nuevo, un parámetro de consulta opcional, o un código de estado adicional que no cambie el comportamiento de los existentes: cambio menor.
- Cambiar el método HTTP de un endpoint existente, eliminar un endpoint, modificar el mecanismo de autenticación de forma que invalide credenciales vigentes, o cambiar el significado de un código de estado ya definido: cambio mayor. Requiere una nueva ruta base y coordinación con el Contrato de Datos si el cambio afecta la representación de los recursos.
- Agregar una forma de autenticación nueva que coexiste con las vigentes sin invalidarlas es un cambio menor (criterio aplicado en la versión 1.3 y, de nuevo, en esta versión para el login con tokens de sesión).

La versión 2.0 es un cambio mayor: acompaña al Contrato de Datos 2.0, cuyos cambios incompatibles (Sección 7 de ese documento) alteran el cuerpo de la creación, del reemplazo completo y de la actualización parcial. Por eso se publica bajo la ruta base `/api/v2`. El servicio 2.0 no expone `/api/v1`: los clientes de la versión 1.x (la colección Postman 1.x y `crm_som.py` 1.x) deben actualizarse a la versión 2.0.

Esta ficha documenta la versión **2.0** del contrato operativo, correspondiente a la ruta base `/api/v2`.

---

## 12. Glosario

| Término | Definición |
| --- | --- |
| Contrato Operativo | Documento que define cómo se accede a un servicio: transporte, autenticación, endpoints y manejo de errores. |
| Protocolo | Conjunto de reglas que rigen el intercambio de mensajes entre cliente y servidor (en este caso, HTTP + JSON). |
| Autenticación básica (Basic Auth) | Mecanismo HTTP en que el cliente envía usuario y contraseña codificados en Base64 en el header `Authorization`. La codificación Base64 no cifra: sin TLS, las credenciales viajan legibles. |
| Token de sesión | Credencial temporal emitida por el servicio tras un login exitoso, que reemplaza al usuario y contraseña en las solicitudes siguientes. |
| Clave fija de canal | Credencial permanente asociada a un canal (`GUI` o `CRM`), usada para integración entre sistemas. |
| Parámetro de consulta (query parameter) | Par `nombre=valor` agregado a la URL después del signo `?`, separado de otros por `&`. |
| Paginación | División de un listado extenso en páginas de tamaño fijo, que el cliente solicita una a una. |
| Clave de idempotencia | Identificador enviado por el cliente que permite al servidor reconocer y rechazar una solicitud repetida. |
| Idempotencia | Propiedad de una operación cuyo resultado no cambia si se repite más de una vez con los mismos parámetros. |
| Header HTTP | Metadato enviado junto a una solicitud o respuesta HTTP, fuera del cuerpo del mensaje. |
| Status Code | Código numérico HTTP que indica el resultado de una solicitud. |
| OpenAPI / Swagger | Especificación estándar para describir una API REST (OpenAPI) y herramienta que la presenta como página navegable e interactiva (Swagger UI). |
| Webhook | Mecanismo por el cual un servicio notifica, por su propia iniciativa, un evento a una URL registrada por el cliente. |
| Callback | Sinónimo de webhook en este documento: una llamada HTTP que el servidor realiza hacia el cliente. |
| Canal de origen | Identificador (`CRM` o `GUI`) del tipo de cliente que ejecutó una operación, derivado de la credencial usada. |
| Conciliación | Proceso de comparar el estado local de un receptor contra el estado real del servicio, para detectar eventos que no llegaron a notificarse. |
| Volumen Docker | Almacenamiento administrado por Docker, independiente del ciclo de vida del contenedor, donde se guardan datos que deben sobrevivir a su reinicio o recreación. |

---

*Documento de referencia — no es un procedimiento (MOP). Se actualiza cuando cambia el protocolo, la autenticación o los endpoints del servicio; los cambios en la estructura de datos se documentan en la ficha de Contrato de Datos asociada.*
