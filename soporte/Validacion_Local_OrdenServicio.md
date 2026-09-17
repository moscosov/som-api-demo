# Validación Local — API Orden de Servicio

Nota de trabajo personal, no un entregable del curso. Objetivo: validar que `som_api_demo.py` instala y corre sin fricción antes de avanzar a la Etapa 2 (MOP para estudiantes, despliegue en AWS/Ubuntu).

Documentos de referencia durante la prueba: `GuiaRapida_OrdenServicio_DuocUC.md` (comandos) y `Contrato_Operativo_OrdenServicio_DuocUC.md` (si algo no se comporta como se espera).

---

## Qué se va a validar

- Que el entorno virtual se crea y las dependencias instalan sin errores, en ambos equipos.
- Que el servicio arranca y queda escuchando en `0.0.0.0:8081`.
- Que los 6 comandos de la Guía Rápida responden como se documentó, en `localhost` (laptop) y a través de la red local (laptop → kuberlab).

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

## Resultado de la validación

*(completar después de probar)*

- [ ] Escenario A — entorno virtual e instalación sin errores
- [ ] Escenario A — servicio arranca y escucha en `0.0.0.0:8081`
- [ ] Escenario A — los 6 comandos responden como se documentó en la Guía Rápida
- [ ] Escenario B — entorno virtual e instalación sin errores en kuberlab
- [ ] Escenario B — servicio alcanzable desde el laptop vía `192.168.1.4:8081`
- [ ] Escenario B — los 6 comandos responden como se documentó en la Guía Rápida

**Observaciones / ajustes antes de avanzar a la Etapa 2:**

_(pendiente)_
