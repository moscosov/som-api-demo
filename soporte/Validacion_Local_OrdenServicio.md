# Validación Local — API Orden de Servicio

Nota de trabajo personal, no un entregable del curso. Objetivo: validar que `som_api_demo.py` instala y corre sin fricción antes de usarlo en clase. El Escenario C valida además el flujo de webhook completo entre `som-api` y `crm-som` 2.0 sin Docker, y el Escenario D, el mismo flujo con el compose `som-crm`.

Documentos de referencia durante la prueba: `GuiaRapida_OrdenServicio_DuocUC.md` (comandos), `Contrato_Operativo_OrdenServicio_DuocUC.md` (si algo no se comporta como se espera, Sección 6 para el webhook), `Guia_Integracion_CRM_SomApi_OrdenServicio_DuocUC.md` (comportamiento esperado de `crm-som` 2.0) y `crm/crm_som.py` (fuente de verdad de ese comportamiento).

---

## Qué se va a validar

- Que el entorno virtual se crea y las dependencias instalan sin errores, en ambos equipos.
- Que el servicio arranca y queda escuchando en `0.0.0.0:8081`.
- Que los 6 comandos de la Guía Rápida responden como se documentó, en `localhost` (laptop) y a través de la red local (laptop → kuberlab).
- Que el flujo de webhook funciona de punta a punta con `crm-som` 2.0: registro automático, creación con `com_id` del rango reservado, disparo no bloqueante desde `som-api`, recepción en `crm-som`, registro de un intento fallido en `GET /webhooks/fallos` y recuperación del registro después de un reinicio de `som-api`.
- Que el mismo flujo funciona con ambos servicios en contenedores, conectados por nombre en la red `som-network`, con los datos persistidos en el volumen.

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

## Escenario C — `crm-som` 2.0 sin Docker (mismo laptop)

Objetivo: validar el flujo completo entre `som-api` 2.1 y `crm-som` 2.0 como procesos locales, antes de introducir los contenedores. Todos los comandos se ejecutan desde la carpeta del repositorio (`~/som-api-demo`, rama `desarrollo`).

### 1. Activar el entorno virtual e instalar las dependencias

`crm_som.py` usa `flask` y `requests`, ya incluidas en el `requirements.txt` de la raíz. Se reutiliza el entorno virtual del Escenario A:

```bash
source ~/som-api-venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 2. Ejecutar `som-api` (terminal 1)

`som-api` 2.1 guarda sus datos en `data/som_data.json`, en la carpeta desde donde se ejecuta. Si ese archivo ya existe con órdenes de otras pruebas, los `com_id` del paso 5 pueden ser distintos de los de esta guía. Para partir de cero, apartarlo antes de arrancar:

```bash
mv data/som_data.json data/som_data.json.bak
```

```bash
python3 som_api_demo.py
```

Confirmar en la salida el mensaje `SOM API Demo v2 escuchando en el puerto 8081`.

### 3. Ejecutar `crm-som` (terminal 2)

Los valores por defecto de `crm_som.py` usan nombres de contenedor (`som-api`, `crm-som`), que no existen fuera de Docker. Se sobrescriben dos variables; la clave del canal CRM y el secreto del webhook ya coinciden con los de `som-api`. Ejecutar estos cuatro comandos, uno a la vez:

```bash
source ~/som-api-venv/bin/activate
```

```bash
export SOM_API_URL=http://localhost:8081/api/v2
```

```bash
export WEBHOOK_URL_PROPIA=http://localhost:8082/webhooks/ordenes
```

```bash
python3 crm/crm_som.py
```

Confirmar en la salida `crm-som v2.0 escuchando en el puerto 8082` y, segundos después, la línea `WEBHOOK_REGISTRADO | url=http://localhost:8082/webhooks/ordenes reregistro cada 60 s`.

### 4. Definir las variables de prueba (terminal 3)

Para que los comandos siguientes quepan en una línea. Ejecutar estos tres comandos, uno a la vez:

```bash
SOM=http://localhost:8081/api/v2
```

```bash
CRM=http://localhost:8082
```

```bash
CLAVE='X-API-KEY: DUOC-CUY6142-DEMO'
```

### 5. Confirmar el estado de `crm-som`

```bash
curl -s "$CRM/estado"
```

Respuesta esperada (`200`): `"version": "2.0"`, `"webhook": {"registrado": true, ...}` y `"com_id": {"rango": "9000000-9999999", "siguiente": null}`. El siguiente `com_id` aparece recién después de la primera creación.

### 6. Crear un `ALTA` vía `crm-som` (canal CRM), sin `com_id`

Todo el bloque es un solo comando: el `\` al final de la línea indica que continúa en la siguiente.

```bash
curl -s -X POST "$CRM/ordenes" -H 'Content-Type: application/json' \
  -d '{"tipo_orden":"ALTA","cliente_id":"CL-10457","tipo_servicio":"INTERNET","offer_id":"200102"}'
```

Respuesta esperada (`201`): `"com_id": "9000001"`, `"subscription_id": "20000001"`, `"estado": "RECIBIDA"`. Copiar el `id` devuelto.

### 7. Confirmar la orden en `som-api` (canal GUI)

```bash
curl -s "$SOM/ordenes?com_id=9000001" -H "$CLAVE"
```

Debe devolver la misma orden: `crm-som` no es la fuente de verdad.

### 8. Transicionar la orden vía canal GUI, no vía `crm-som`

```bash
ORDEN=<ID_ORDEN>
```

```bash
curl -s -X PATCH "$SOM/ordenes/$ORDEN" -H "$CLAVE" -H 'Content-Type: application/json' -d '{"estado":"EN_PROGRESO"}'
```

Confirmar en la respuesta `"notificacion_webhook": "pendiente"`.

### 9. Confirmar la recepción en `crm-som`

En la terminal 2 debe aparecer una línea `WEBHOOK_RECIBIDO | com_id=9000001 tipo_orden=ALTA operacion=PATCH estado=RECIBIDA->EN_PROGRESO canal_origen=GUI`. Confirmar también el contador:

```bash
curl -s "$CRM/eventos"
```

Respuesta esperada: `"total": 1`, con el evento completo (incluye `com_id`, `tipo_orden` y `subscription_id`).

### 10. Revisar la interfaz web

En el navegador:

```text
http://localhost:8082/
```

Confirmar: indicador **webhook registrado** en verde, la orden `9000001` en la tabla y el evento del paso 9 en **Notificaciones recibidas**. Completar la orden con un `PATCH` a `COMPLETADA` (mismo comando del paso 8, cambiando el estado) y verificar que la tabla se actualiza sola. Crear desde la interfaz una `RELOCALIZACION` sobre la `20000001` (punto actual `2.5`, `1.75`, `Living`; destino `6.125`, `4.5`, `Dormitorio 2`) y abrir su **Trazabilidad**: 6,375 m, 00:37:45 y cuatro pasos.

### 11. Provocar y verificar un fallo de entrega

Crear primero una orden nueva vía `crm-som` (paso 6) y asignar su `id` a `ORDEN` (paso 8). Luego detener `crm-som` con `Ctrl+C` en la terminal 2, transicionar la orden vía canal GUI (paso 8, segundo comando) y consultar la conciliación con `crm-som` todavía detenido:

```bash
curl -s "$SOM/webhooks/fallos" -H "$CLAVE"
```

Confirmar una entrada para esa orden, con `motivo` de conexión rechazada.

### 12. Verificar la recuperación del registro después de un reinicio de `som-api`

Volver a ejecutar `crm-som` en la terminal 2 (paso 3, último comando; las variables siguen definidas en esa terminal). Luego detener `som-api` con `Ctrl+C` en la terminal 1 y mantenerlo detenido al menos 60 segundos: en la terminal 2 debe aparecer `WEBHOOK_NO_REGISTRADO | som-api inalcanzable: ConnectionError`. Volver a ejecutar `som-api` (paso 2, último comando): en menos de 5 segundos debe aparecer `WEBHOOK_RECUPERADO`. Las órdenes siguen ahí, porque se guardaron en `data/som_data.json`.

### 13. Ejecutar las pruebas automatizadas

Detener ambos servicios (`Ctrl+C` en las terminales 1 y 2): las pruebas levantan sus propias copias en los puertos `8081` y `8082`, con datos temporales.

```bash
python3 pruebas/prueba_crm_som_v2.py $PWD/som_api_demo.py $PWD/crm/crm_som.py
```

Resultado esperado: `42/42 pruebas OK`.

La prueba de la interfaz usa un navegador sin pantalla (Playwright con Chromium). Instalar ambos una sola vez:

```bash
pip install playwright
```

```bash
python3 -m playwright install chromium
```

```bash
python3 pruebas/prueba_interfaz_crm_som_v2.py $PWD/som_api_demo.py $PWD/crm/crm_som.py /tmp/captura_crm.png
```

Resultado esperado: `14/14 pruebas de interfaz OK` y una captura de la interfaz en `/tmp/captura_crm.png`.

### 14. Revisar el log de `som-api`

```bash
grep -E 'POST /api/v2/ordenes|PATCH' som_api_demo.log
```

La creación del paso 6 debe aparecer con `canal=CRM` y las transiciones de los pasos 8 y 11 con `canal=GUI`. También aparecen las líneas periódicas `POST /api/v2/webhooks` con `canal=CRM`: son el registro periódico de `crm-som`.

---

## Escenario D — compose `som-crm` (mismo laptop, con Docker)

Objetivo: validar los dos servicios en contenedores, conectados por nombre en la red `som-network`, tal como se despliegan para la demostración (Guía de Integración CRM, Sección 10). Requiere Docker con el plugin `docker compose`.

### 1. Confirmar que los puertos están libres

El compose `docker-compose/som-api` y los procesos del Escenario C no deben estar corriendo:

```bash
sudo ss -tulpn | grep -E ':(8081|8082)\b'
```

No debe devolver ningún resultado.

### 2. Construir la imagen de `crm-som`

Mientras `moscosov/crm-som-demo:v2.0` no esté publicada en Docker Hub, se construye localmente, desde la carpeta del repositorio:

```bash
docker build -t moscosov/crm-som-demo:v2.0 crm
```

### 3. Levantar ambos servicios

```bash
cd docker-compose/som-crm
```

```bash
docker compose up -d
```

### 4. Verificar el estado y el registro del webhook

```bash
docker compose ps
```

Ambos servicios deben indicar `Up ... (healthy)`.

```bash
docker compose logs crm-som
```

Debe aparecer `WEBHOOK_REGISTRADO | url=http://crm-som:8082/webhooks/ordenes reregistro cada 60 s`: `som-api` llama a `crm-som` por su nombre de contenedor.

### 5. Repetir el flujo de webhook

Repetir los pasos 4, 6, 8 y 9 del Escenario C: los puertos publicados son los mismos (`8081` y `8082` en `localhost`). Confirmar que `"total"` de `GET /eventos` aumenta con cada transición.

### 6. Verificar que los procesos corren como usuario no-root

```bash
docker compose exec crm-som id
```

```bash
docker compose exec som-api id
```

Ambos deben responder `uid=1000(appuser)`.

### 7. Verificar la recuperación después de reiniciar `som-api`

```bash
docker compose restart som-api
```

Esperar hasta 60 segundos y confirmar que el webhook vuelve a estar registrado:

```bash
curl -s http://localhost:8082/estado
```

Luego transicionar otra vez la orden (paso 8 del Escenario C, a `COMPLETADA`) y confirmar que el evento llega a `crm-som`.

### 8. Verificar la persistencia de los datos y de la secuencia de `com_id`

```bash
docker compose down
```

```bash
docker compose up -d
```

Crear otra orden vía `crm-som` (paso 6 del Escenario C, con `"tipo_servicio":"TV"` y `"offer_id":"300101"`). Su `com_id` debe continuar la secuencia (`9000002` si no hubo otras creaciones), porque `crm-som` la reconstruye desde los datos de `som-api`, que se conservaron en el volumen.

### 9. Limpiar

Detener los servicios y borrar el volumen de datos de esta prueba:

```bash
docker compose down -v
```

---

## Resultado de la validación

- [x] Escenario A — entorno virtual e instalación sin errores
- [x] Escenario A — servicio arranca y escucha en `0.0.0.0:8081`
- [x] Escenario A — los 6 comandos responden como se documentó en la Guía Rápida
- [ ] Escenario B — entorno virtual e instalación sin errores en kuberlab
- [ ] Escenario B — servicio alcanzable desde el laptop vía `192.168.1.4:8081`
- [ ] Escenario B — los 6 comandos responden como se documentó en la Guía Rápida
- [ ] Escenario C — `crm-som` 2.0 arranca, se registra solo y `GET /estado` informa `"registrado": true`
- [ ] Escenario C — creación vía `crm-som` sin `com_id` recibe `9000001` y coincide con lo visto en `som-api`
- [ ] Escenario C — `PATCH` vía canal GUI dispara el webhook y `crm-som` lo recibe (`GET /eventos`)
- [ ] Escenario C — la interfaz web muestra la notificación y actualiza la tabla sin recargar; trazabilidad de la relocalización correcta
- [ ] Escenario C — con `crm-som` detenido, el intento fallido aparece en `GET /webhooks/fallos`
- [ ] Escenario C — después de reiniciar `som-api`, `crm-som` recupera el registro (`WEBHOOK_RECUPERADO`)
- [ ] Escenario C — pruebas automatizadas: 42/42 de integración y 14/14 de interfaz
- [ ] Escenario D — imagen de `crm-som` construida y ambos contenedores `healthy`
- [ ] Escenario D — webhook registrado por nombre de contenedor y entregado
- [ ] Escenario D — ambos procesos corren como `appuser` (UID 1000)
- [ ] Escenario D — recuperación del registro después de `docker compose restart som-api`
- [ ] Escenario D — datos y secuencia de `com_id` conservados después de `down` y `up`

**Observaciones / ajustes:**

Escenario A confirmado en `g10suse16`. Evidencia real revisada: semántica de `PUT` correcta (reemplaza campos editables, no toca `id`/`estado`/`fecha_creacion`), un caso real de `422` por enum case-sensitive, y una transición `DELETE` → `CANCELADA` verificada. Sin hallazgos que requieran ajustar el código o los contratos.

Escenario C con `crm-som` 1.x confirmado en `g10suse16` (27/09/2026), flujo completo verificado contra `som_api_demo.log`. Registro histórico: ese escenario usaba la ruta `/api/v1` y el registro manual del webhook, reemplazados por la versión actual de este documento.

- `crm-som` incorporó un panel web (`GET /`) además de la API; el estado en JSON quedó en `GET /estado`. Corregido en este documento — no requiere cambio en el código, solo era un desajuste con la documentación de prueba.
- Registro de webhook (`POST /webhooks` → `201`), creación de orden vía canal CRM (`POST /ordenes` en `crm-som` → `201`, `canal=CRM` en el log de `som-api`), transición vía canal GUI con disparo de webhook (`PATCH` → `200` con `notificacion_webhook: pendiente`; `som-api` confirma el estado contra sí misma antes de notificar — línea `GET ... canal=CRM` previa al `WEBHOOK ... -> 200`), y actualización de la caché local en `crm-som` — todo verificado.
- Fallo de entrega simulado deteniendo `crm-som`: quedó registrado en `GET /webhooks/fallos` con `motivo`, `canal_origen`, `url_destino` y `orden_id` correctos (`Connection refused`, sin reintentos automáticos, según Contrato Operativo Sección 6.7).
- Sin hallazgos que requieran ajustar el código o los contratos.

Validación de desarrollo de `crm-som` 2.0 (12/10/2026), en el entorno de desarrollo, no en `g10suse16`:

- Escenario C automatizado: 42/42 pruebas de integración (creación de los cuatro tipos, `com_id` sin huecos ante un `422`, colisión con reintento, continuidad tras reiniciar `crm-som`, 10 creaciones simultáneas sin duplicados, rango agotado, clave incorrecta, webhook por ambos canales y recuperación tras reiniciar `som-api`) y 14/14 de interfaz en Chromium.
- Escenario D: ambos contenedores `healthy` y como `appuser`, webhook entregado por nombre de contenedor, recuperado después de `docker compose restart som-api`, y datos y secuencia conservados después de `down` y `up`.
- Comportamiento esperado confirmado: si `som-api` se reinicia y vuelve antes de que `crm-som` lo note, la notificación inmediatamente posterior se pierde hasta el siguiente ciclo de registro (60 segundos). La tabla de la interfaz igual muestra el estado correcto, porque se lee desde `som-api`.

Pendiente: Escenario B en `kuberlab`, y Escenarios C y D de `crm-som` 2.0 en `g10suse16`.
