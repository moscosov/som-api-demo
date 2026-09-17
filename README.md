# SOM API Demo — Orden de Servicio

API REST demo del proceso eTOM **Order Handling** (Process Identifier 1.1.1.5), alineada conceptualmente con el API abierto de TM Forum **TMF641 (Service Ordering Management)**, desarrollada como material de apoyo para el curso **CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana** (Duoc UC, Escuela de Informática y Telecomunicaciones).

Permite registrar, dar seguimiento y cerrar una Orden de Servicio a lo largo de su ciclo de vida, replicando en versión simplificada el tipo de interacción que resuelve un sistema real de Service Order Management (SOM) en un proveedor de telecomunicaciones.

## Contexto académico

Complementa las Actividades 2.3 y 2.4 de EA2 (Fundamentos y Consumo de APIs), centradas en el consumo de APIs ya existentes: este proyecto permite además observar el lado que **expone** el servicio. El detalle completo de propósito, actores y casos de uso está en `docs/1_1_EspecificacionFuncional_OrdenServicio_DuocUC.md`.

## Ciclo de vida del recurso

```
RECIBIDA ──► EN_PROGRESO ──► COMPLETADA
    │              │
    └──────────────┴──────► CANCELADA
```

Una orden en `COMPLETADA` o `CANCELADA` es un estado terminal: ningún actor puede modificarla ni revertirla. Detalle completo de la máquina de estados en `docs/Contrato_Datos_OrdenServicio_DuocUC.md`.

## Requisitos

- Python 3.12+
- Dependencias: `flask`, `jsonschema` (ver `requirements.txt`)
- Docker (opcional, para ejecución contenerizada)

## Ejecución local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python som_api_demo.py
```

El servicio queda disponible en `http://localhost:8081/api/v1/ordenes` (puerto configurable con la variable de entorno `PORT`). Los eventos se registran en consola y en `som_api_demo.log`.

## Ejecución con Docker

```bash
docker build -t som-api-demo .
docker run -p 8081:8081 som-api-demo
```

La imagen usa build multi-stage y ejecuta el proceso con un usuario no root (`appuser`). Detalle de la contenerización en `docs/soporte/Guia_Fundamentos_Docker_OrdenServicio.md`.

## Autenticación

Todos los endpoints requieren el header `X-API-Key` con el valor fijo `DUOC-CUY6142-DEMO` (uso exclusivo de este entorno demo). Detalle en `docs/Contrato_Operativo_OrdenServicio_DuocUC.md`, Sección 4.

## Uso rápido

```bash
curl -X POST http://localhost:8081/api/v1/ordenes \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"CL-10457","tipo_servicio":"INTERNET","prioridad":"ALTA"}'
```

Flujo completo (crear, avanzar y completar una orden) y el resto de las operaciones (`GET`, `PUT`, `PATCH`, `DELETE`) en `docs/GuiaRapida_OrdenServicio_DuocUC.md`. Colección lista para importar en Postman: `postman/Postman_Coleccion_OrdenServicio_DuocUC.json`.

## Almacenamiento

En memoria, sin persistencia — el estado se reinicia al reiniciar el proceso. Exclusión declarada explícitamente en `docs/Contrato_Operativo_OrdenServicio_DuocUC.md`, Sección 9.

## Estructura del repositorio

```
som_api_demo/
├── som_api_demo.py
├── Dockerfile
├── requirements.txt
├── docs/
│   ├── 1_1_EspecificacionFuncional_OrdenServicio_DuocUC.md
│   ├── DisenoFuncional_OrdenServicio_DuocUC.md
│   ├── Contrato_Datos_OrdenServicio_DuocUC.md
│   ├── Contrato_Operativo_OrdenServicio_DuocUC.md
│   ├── GuiaRapida_OrdenServicio_DuocUC.md
│   └── soporte/
│       ├── Validacion_Local_OrdenServicio.md
│       └── Guia_Fundamentos_Docker_OrdenServicio.md
└── postman/
    └── Postman_Coleccion_OrdenServicio_DuocUC.json
```

## Documentación

| Documento | Contenido |
| --- | --- |
| `docs/1_1_EspecificacionFuncional_OrdenServicio_DuocUC.md` | Propósito de negocio, actores, casos de uso |
| `docs/DisenoFuncional_OrdenServicio_DuocUC.md` | Arquitectura interna y decisiones de diseño |
| `docs/Contrato_Datos_OrdenServicio_DuocUC.md` | Schema del recurso, reglas de validación, máquina de estados |
| `docs/Contrato_Operativo_OrdenServicio_DuocUC.md` | Endpoints, autenticación, códigos de estado HTTP |
| `docs/GuiaRapida_OrdenServicio_DuocUC.md` | Comandos `curl` listos para copiar y pegar |
| `docs/soporte/Validacion_Local_OrdenServicio.md` | Guía de pruebas locales |
| `docs/soporte/Guia_Fundamentos_Docker_OrdenServicio.md` | Fundamentos de la contenerización del servicio |

## Alcance

Fuera de alcance de forma deliberada: facturación (Billing), gestión de incidentes sobre un servicio activo (Assurance), integración con sistemas externos reales, y gestión de usuarios o permisos diferenciados por actor. Detalle en `docs/1_1_EspecificacionFuncional_OrdenServicio_DuocUC.md`, Sección 8.

## Licencia

Material académico desarrollado para CUY6142, Escuela de Informática y Telecomunicaciones, Duoc UC.
