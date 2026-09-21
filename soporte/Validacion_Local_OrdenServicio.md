# Validación Local — API Orden de Servicio

Nota de trabajo personal, no un entregable del curso. Objetivo: validar que `som_api_demo.py` instala y corre sin fricción antes de avanzar a la Etapa 2 (MOP para estudiantes, despliegue en AWS/Ubuntu). El Escenario C valida además el flujo de webhook completo (`som-api` + `crm-som`) antes de dockerizar ambos servicios.

Documentos de referencia durante la prueba: `GuiaRapida_OrdenServicio_DuocUC.md` (comandos), `Contrato_Operativo_OrdenServicio_DuocUC.md` (si algo no se comporta como se espera, Sección 6 para el webhook), y `crm_som.py` (fuente de verdad del comportamiento de `crm-som`).

---

## Qué se va a validar

- Que el entorno virtual se crea y las dependencias instalan sin errores, en ambos equipos.
- Que el servicio arranca y queda escuchando en `0.0.0.0:8081`.
- Que los 6 comandos de la Guía Rápida responden como se documentó, en `localhost` (laptop) y a través de la red local (laptop → kuberlab).
- Que el flujo de webhook funciona de punta a punta: registro, disparo no bloqueante desde `som-api`, recepción y actualización de caché local en `crm-som`, y que un intento fallido queda registrado en `GET /webhooks/fallos`.

---

## Escenario A — todo en el laptop (`g10suse16`, `192.168.1.112`)

### 1. Crear el entorno virtual e instalar dependencias

```bash
python3 -m venv ~/som-api-venv
source ~/som-api-venv/bin/activate
pip install -r requirements.txt
```

### 2. Ejecutar el servicio

```bash
python3 som_api_demo.py
```

Confirmar en la salida: el mensaje `SOM API Demo escuchando en el puerto 8081` y que Flask reporta `Running on all addresses (0.0.0.0)` con `127.0.0.1:8081` y `192.168.1.112:8081` listados.

### 3. Probar desde otra terminal del mismo laptop

No hace falta activar el entorno virtual para usar `curl` — solo para correr el servidor. Usar los 6 comandos de `GuiaRapida_OrdenServicio_DuocUC.md` con:

```
<HOST> = localhost
```

### 4. Detener el servicio

`Ctrl+C` en la terminal donde corre. Revisar que `som_api_demo.log` haya quedado con una línea por cada solicitud probada.

---

## Escenario B — servidor en kuberlab (`192.168.1.4`), cliente en el laptop

### 1. Copiar los archivos a kuberlab

```bash
scp som_api_demo.py requirements.txt <usuario>@192.168.1.4:~/som-api-demo/
```

(Ajustar usuario y ruta destino según cómo sueles transferir archivos a kuberlab.)

### 2. En kuberlab — crear el entorno virtual e instalar dependencias

```bash
cd ~/som-api-demo
python3 -m venv som-api-venv
source som-api-venv/bin/activate
pip install -r requirements.txt
```

### 3. Ejecutar el servicio en kuberlab

```bash
python3 som_api_demo.py
```

Si `firewalld` bloquea el puerto entrante, abrirlo (fuera del alcance de los contratos, es configuración de tu red — ya lo tienes considerado):

```bash
firewall-cmd --add-port=8081/tcp
```

### 4. Desde el laptop, probar los 6 comandos con

```
<HOST> = 192.168.1.4
```

### 5. Detener el servicio en kuberlab

`Ctrl+C`. Revisar `som_api_demo.log` en kuberlab.

---

## Escenario C — webhook + crm-som (mismo laptop, sin Docker)

Objetivo: validar el flujo completo de notificación asíncrona — registro, disparo no bloqueante, recepción, actualización de caché local y conciliación de fallos — antes de introducir la complejidad adicional de `som-network` y los contenedores.

### 1. Instalar dependencias de `crm-som`

`crm_som.py` usa las mismas dependencias que `som_api_demo.py` (`flask`, `requests`). Puede reutilizarse el mismo entorno virtual del Escenario A.

```bash
source ~/som-api-venv/bin/activate
```

### 2. Ejecutar `som-api` (si no sigue corriendo del Escenario A)

```bash
python3 som_api_demo.py
```

### 3. Ejecutar `crm-som` en otra terminal, apuntando a `som-api` en `localhost`

Los valores por defecto de `crm_som.py` asumen resolución de nombre de contenedor (`som-api`), que todavía no existe en este escenario — hay que sobrescribirlos vía variables de entorno:

```bash
export SOM_API_URL=http://localhost:8081/api/v1
export SOM_API_KEY=DUOC-CUY6142-DEMO-CRM
export WEBHOOK_SECRET=DUOC-CUY6142-DEMO-WEBHOOK-SECRET
python3 crm_som.py
```

Confirmar en la salida que `crm-som` queda escuchando en `0.0.0.0:8082`.

### 4. Confirmar que `crm-som` está arriba

```bash
curl http://localhost:8082/
```

Respuesta esperada (`200`): estado del servicio, con el contador de caché en `0`.

### 5. Registrar el webhook en `som-api`, apuntando a `crm-som`

Vía canal GUI (Postman/curl), igual que el resto de la operación manual:

```bash
curl -X POST http://localhost:8081/api/v1/webhooks \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://localhost:8082/webhooks/ordenes"}'
```

### 6. Crear una orden vía `crm-som` (canal CRM)

```bash
curl -X POST http://localhost:8082/ordenes \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":"CL-10457","tipo_servicio":"INTERNET","prioridad":"ALTA"}'
```

Confirmar que el `id` devuelto coincide con el que aparece en `GET http://localhost:8081/api/v1/ordenes` (canal GUI) — `crm-som` no es la fuente de verdad, solo un proxy con caché local.

### 7. Transicionar la orden vía canal GUI (Postman/curl) — no vía `crm-som`

```bash
curl -X PATCH http://localhost:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"estado":"EN_PROGRESO"}'
```

Confirmar en la respuesta el campo `"notificacion_webhook": "pendiente"`.

### 8. Confirmar la recepción en `crm-som`

En la consola de `crm-som` debe aparecer el evento recibido en `POST /webhooks/ordenes`, y la confirmación posterior contra `som-api` (`GET /ordenes/{id}`) que usa para no confiar directamente en el payload liviano del webhook. Verificar que la caché local se actualizó:

```bash
curl http://localhost:8082/ordenes/<ID_ORDEN>
```

Debe mostrar `"estado": "EN_PROGRESO"`.

### 9. Provocar y verificar un fallo de entrega

Detener `crm-som` (`Ctrl+C`) y repetir una transición sobre la misma orden vía canal GUI:

```bash
curl -X PATCH http://localhost:8081/api/v1/ordenes/<ID_ORDEN> \
  -H "X-API-Key: DUOC-CUY6142-DEMO" \
  -H "Content-Type: application/json" \
  -d '{"estado":"COMPLETADA"}'
```

Luego, con `crm-som` todavía detenido, consultar la conciliación en `som-api`:

```bash
curl http://localhost:8081/api/v1/webhooks/fallos \
  -H "X-API-Key: DUOC-CUY6142-DEMO"
```

Confirmar que aparece una entrada para esta orden.

### 10. Detener ambos servicios

`Ctrl+C` en cada terminal. Revisar `som_api_demo.log` — debe incluir la línea `canal=CRM` para la creación del paso 6 y `canal=GUI` para las transiciones de los pasos 7 y 9.

---

## Resultado de la validación

*(completar después de probar)*

- [x] Escenario A — entorno virtual e instalación sin errores
- [x] Escenario A — servicio arranca y escucha en `0.0.0.0:8081`
- [x] Escenario A — los 6 comandos responden como se documentó en la Guía Rápida
- [ ] Escenario B — entorno virtual e instalación sin errores en kuberlab
- [ ] Escenario B — servicio alcanzable desde el laptop vía `192.168.1.4:8081`
- [ ] Escenario B — los 6 comandos responden como se documentó en la Guía Rápida
- [ ] Escenario C — `crm-som` arranca y `GET /` responde con el estado del servicio
- [ ] Escenario C — registro de webhook en `som-api` exitoso (`201`)
- [ ] Escenario C — creación de orden vía `crm-som` (canal CRM) coincide con lo visto en `som-api`
- [ ] Escenario C — `PATCH` vía canal GUI dispara el webhook y `crm-som` recibe y actualiza su caché local
- [ ] Escenario C — con `crm-som` detenido, el intento fallido aparece en `GET /webhooks/fallos`

**Observaciones / ajustes antes de avanzar a la Etapa 2:**

Escenario A confirmado en `g10suse16`. Evidencia real revisada: semántica de `PUT` correcta (reemplaza campos editables, no toca `id`/`estado`/`fecha_creacion`), un caso real de `422` por enum case-sensitive, y una transición `DELETE` → `CANCELADA` verificada. Sin hallazgos que requieran ajustar el código o los contratos.

Pendiente: Escenario B en `kuberlab`. Pendiente: Escenario C (webhook + `crm-som`, recién incorporado — sin ejecutar todavía).
