# SOM API Demo — Orden de Servicio

API REST demo del proceso eTOM **Order Handling** (Process Identifier 1.1.1.5), alineada conceptualmente, sin pretender conformidad ni certificación, con los APIs abiertos de TM Forum **TMF641** (Service Ordering Management), **TMF638** (Service Inventory Management) y **TMF620** (Product Catalog Management). Desarrollada como material de apoyo para el curso **CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana** (Duoc UC, Escuela de Informática y Telecomunicaciones).

Simula, en versión simplificada, el sistema de Service Order Management (SOM) de un proveedor de telecomunicaciones: órdenes de alta, baja, cambio de oferta y relocalización de un punto de red, con suscripciones, catálogo de ofertas, trazabilidad y notificaciones asíncronas (webhook).

## Contexto académico

Complementa las Actividades 2.3 y 2.4 de EA2 (Fundamentos y Consumo de APIs): el estudiante consume el servicio con Postman, `curl` y scripts Python, y observa además el lado que lo **expone**. Es la base de la actividad formativa 2.4.2. El detalle de propósito, actores y casos de uso está en la Especificación Funcional (`docs/1_1_EspecificacionFuncional_OrdenServicio_DuocUC_v2.md`).

## Componentes

| Componente | Versión | Archivo | Imagen en Docker Hub | Puerto |
| --- | --- | --- | --- | --- |
| `som-api` — el SOM, fuente de verdad de las órdenes | 2.1 | `som_api_demo.py` | `moscosov/som-api-demo:v2.1` | `8081` |
| `crm-som` — Sistema Cliente de referencia (canal CRM), con interfaz web | 2.0 | `crm/crm_som.py` | `moscosov/crm-som-demo:v2.0` | `8082` |

`crm-som` se usa como demostración del docente: crea órdenes de los cuatro tipos con su propio número de orden comercial, recibe las notificaciones de `som-api` y las muestra en su interfaz. Su integración se documenta en `soporte/Guia_Integracion_CRM_SomApi_OrdenServicio_DuocUC.md`.

## Requisitos

- Python 3.12 o superior, con `flask`, `jsonschema` y `requests` (ver `requirements.txt`), para ejecutar sin Docker.
- Docker con el plugin `docker compose`, para ejecutar con contenedores.

## Ejecución local de `som-api`

Crear y activar un entorno virtual:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar el servicio:

```bash
python3 som_api_demo.py
```

La documentación navegable (Swagger UI) queda en `http://localhost:8081/api/v2/docs`. Los datos se guardan en `data/som_data.json` (variable `SOM_DATA_FILE`) y sobreviven al reinicio del proceso. El registro de solicitudes queda en consola y en `som_api_demo.log`.

## Ejecución con Docker Compose

### Solo `som-api`

Es el despliegue que usan los estudiantes:

```bash
cd docker-compose/som-api
```

```bash
docker compose up -d
```

### `som-api` y `crm-som` (demostración del docente)

```bash
cd docker-compose/som-crm
```

```bash
docker compose up -d
```

La interfaz de `crm-som` queda en `http://localhost:8082/` y su estado en JSON en `http://localhost:8082/estado`. `crm-som` se registra solo como receptor del webhook de `som-api` y repite el registro cada 60 segundos.

Los dos compose no pueden correr al mismo tiempo en el mismo equipo: ambos usan el contenedor `som-api` y el puerto `8081`. Cada uno tiene su propio volumen de datos. `docker compose down` conserva los datos; `docker compose down -v` los borra.

## Autenticación

Todos los endpoints, salvo el login y la documentación, exigen el header `X-API-KEY` (o el parámetro `key` en la URL) con una de estas credenciales:

| Credencial | Canal | Cómo se obtiene |
| --- | --- | --- |
| Token de sesión | `GUI` o `CRM`, según el usuario | `POST /api/v2/loginViaBasic` con autenticación básica: usuario `gui` o `crm`, contraseña `Cuy6142!` |
| `DUOC-CUY6142-DEMO` | `GUI` | Clave fija, para integración entre sistemas |
| `DUOC-CUY6142-DEMO-CRM` | `CRM` | Clave fija, la que usa `crm-som` |

Valores exclusivos de este entorno de demostración. Detalle en el Contrato Operativo, Sección 4.

## Uso rápido

Iniciar sesión y guardar la respuesta en una variable:

```bash
RESPUESTA=$(curl -s -X POST http://localhost:8081/api/v2/loginViaBasic -u 'gui:Cuy6142!')
```

Extraer el token de la respuesta:

```bash
TOKEN=$(echo "$RESPUESTA" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
```

Crear un `ALTA` (el token contiene `|`: va siempre entre comillas):

```bash
curl -X POST http://localhost:8081/api/v2/ordenes -H "X-API-KEY: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"ALTA","com_id":"1000001","cliente_id":"CL-10457","tipo_servicio":"INTERNET","offer_id":"200102"}'
```

El resto de las operaciones está en la Guía Rápida (`docs/GuiaRapida_OrdenServicio_DuocUC_v2.md`) y en la colección de Postman (`postman/Postman_Coleccion_OrdenServicio_DuocUC_v2.json`).

## Ciclo de vida de una orden

```
RECIBIDA ──► EN_PROGRESO ──► COMPLETADA
    │              │
    └──────────────┴──────► CANCELADA
```

Una orden en `COMPLETADA` o `CANCELADA` es terminal: no se modifica ni se revierte. Las suscripciones tienen su propio ciclo (`PENDIENTE`, `ACTIVA`, `ANULADA`, `BAJA`), que cambia como efecto de las órdenes. Detalle en el Contrato de Datos, Sección 5.

## Número de orden comercial (`com_id`)

Toda orden lleva un `com_id` de 7 dígitos, emitido por quien la solicita y único en todo el SOM. Por convención, el rango `9000000` a `9999999` queda reservado para `crm-som`; los demás solicitantes (Postman, `curl`, scripts) usan `0000000` a `8999999`. `som-api` no valida el rango, solo el formato y la unicidad (Contrato de Datos, Sección 3.5).

## Pruebas

Prueba integral de `som-api`:

```bash
python3 prueba_som_v2.py
```

Pruebas de integración de `crm-som` contra `som-api` (usan los puertos `8081` y `8082`, que deben estar libres):

```bash
python3 pruebas/prueba_crm_som_v2.py $PWD/som_api_demo.py $PWD/crm/crm_som.py
```

Prueba de la interfaz de `crm-som` en un navegador sin pantalla (requiere `playwright` y Chromium):

```bash
python3 pruebas/prueba_interfaz_crm_som_v2.py $PWD/som_api_demo.py $PWD/crm/crm_som.py /tmp/captura_crm.png
```

## Estructura del repositorio

```
som-api-demo/
├── som_api_demo.py              som-api 2.1
├── Dockerfile                   imagen de som-api
├── requirements.txt
├── prueba_som_v2.py             prueba integral de som-api
├── crm/
│   ├── crm_som.py               crm-som 2.0
│   ├── Dockerfile               imagen de crm-som
│   └── requirements.txt
├── docker-compose/
│   ├── som-api/                 solo som-api (estudiantes)
│   └── som-crm/                 som-api y crm-som (demostración del docente)
├── scripts/                     programas de la actividad 2.4.2
├── pruebas/                     pruebas de crm-som
├── postman/                     colección de Postman v2
├── docs/                        especificación, diseño, contratos y guía rápida
├── soporte/                     validación local, Docker, Git e integración CRM
├── diseño_documentacion/        estándar de documentación de la API
├── editor/                      imagen del editor web del ambiente de la actividad 2.4.2
├── k8s/                         manifiestos y script del ambiente k3s de la actividad 2.4.2
├── AAY1110/                     material de otra asignatura (AAY1110, EP2)
└── legacy/                      versión 1.x del servicio y su documentación
```

## Documentación

| Documento | Contenido |
| --- | --- |
| `docs/1_1_EspecificacionFuncional_OrdenServicio_DuocUC_v2.md` | Propósito de negocio, actores y casos de uso |
| `docs/03_DisenoFuncional_OrdenServicio_DuocUC.md` | Arquitectura interna y decisiones de diseño |
| `docs/01_Contrato_Datos_OrdenServicio_DuocUC_v2.md` | Recursos, reglas de validación y de negocio, máquinas de estados, rangos de `com_id` |
| `docs/02_Contrato_Operativo_OrdenServicio_DuocUC_v2.md` | Endpoints, autenticación, parámetros, códigos de estado y webhook |
| `docs/GuiaRapida_OrdenServicio_DuocUC_v2.md` | Comandos `curl` listos para copiar |
| `soporte/Guia_Integracion_CRM_SomApi_OrdenServicio_DuocUC.md` | Integración de `crm-som`, despliegue y guion de la demostración (uso docente) |
| `soporte/Validacion_Local_OrdenServicio.md` | Pruebas locales, con y sin Docker |
| `soporte/Guia_Fundamentos_Docker_OrdenServicio.md` | Fundamentos de la contenerización del servicio |
| `soporte/Ciclo_Git_GitHub_EA2_CUY6142.md` | Ciclo de trabajo con Git y GitHub sobre este proyecto |

## Alcance

Fuera de alcance de forma deliberada: facturación (Billing), gestión de incidentes sobre un servicio activo (Assurance), administración del catálogo, TLS, y usuarios o permisos individuales: la autenticación distingue canales, no personas. Detalle en la Especificación Funcional, Sección 8, y en el Contrato Operativo, Sección 10.

## Licencia

Material académico desarrollado para CUY6142, Escuela de Informática y Telecomunicaciones, Duoc UC.
