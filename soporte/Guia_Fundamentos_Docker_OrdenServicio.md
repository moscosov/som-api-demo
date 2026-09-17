# Guía de fundamentos de Docker — construcción de una imagen con multi-stage build

## 1. Introducción

Esta es una guía básica y de nivel fundamental para aprender a construir imágenes Docker, centrada en dos patrones concretos: el **multi-stage build** y la ejecución del proceso con un **usuario no-root**. Es un documento personal, de uso propio — no es un entregable del curso CUY6142.

La API demo "Orden de Servicio" se usa aquí solo como **pretexto pedagógico**: un código real y ya conocido, sobre el cual practicar la escritura de un `Dockerfile` desde cero, sin partir de una solución resuelta. El objeto de aprendizaje no es la API — es Docker.

Al finalizar esta guía se obtiene:

- Una imagen Docker funcional que ejecuta la API demo.
- Un `Dockerfile` construido con el patrón **multi-stage build** (dos etapas: `builder` y una etapa final).
- Un contenedor que ejecuta el proceso de la aplicación con un **usuario no-root**, alineado con el dominio de minimización de vulnerabilidades de microservicios del programa CKS (Certified Kubernetes Security Specialist).

Las decisiones de diseño detrás de cada elección se explican en el lugar donde corresponden, junto con la instrucción de Dockerfile asociada.

## 2. Prerrequisitos

Antes de comenzar, se debe contar con:

- Docker instalado y funcionando en el sistema anfitrión.

- Los siguientes archivos de origen del proyecto:

  - `som_api_demo.py` — código fuente de la API.
  - `requirements.txt` — lista de dependencias Python del proyecto.

- El siguiente cambio ya aplicado en `som_api_demo.py`, necesario para que el puerto de escucha se pueda configurar desde fuera del contenedor:

  ```python
  PORT = int(os.environ.get("PORT", 8081))
  ```

  Esta línea reemplaza una constante fija de puerto por una lectura de la variable de entorno `PORT`, con `8081` como valor de respaldo si la variable no está definida.

## 3. Preparación del entorno en el sistema anfitrión

Antes de escribir el `Dockerfile`, se crea un directorio de trabajo dedicado en el sistema anfitrión (la máquina donde se ejecuta `docker build`, no dentro de ningún contenedor).

```bash
mkdir -p ~/docker/api_som
cd ~/docker/api_som
```

**Qué hace cada comando:**

- `mkdir -p ~/docker/api_som` — Crea el directorio `api_som` dentro de `~/docker`. La flag `-p` crea también los directorios intermedios que no existan (en este caso, `~/docker`, si aún no existiera) y no genera error si el directorio ya existe.
- `cd ~/docker/api_som` — Cambia el directorio de trabajo de la terminal hacia esa carpeta, que será el **contexto de build** de Docker.

A continuación, se copian o mueven a este directorio los archivos fuente del proyecto:

```bash
cp /ruta/original/som_api_demo.py .
cp /ruta/original/requirements.txt .
```

Al finalizar este paso, el directorio `~/docker/api_som` debe contener:

```
api_som/
├── som_api_demo.py
└── requirements.txt
```

El `Dockerfile` se crea en este mismo directorio, en el paso siguiente. Es importante que todos los archivos que el `Dockerfile` necesita copiar (mediante instrucciones `COPY`) estén dentro de este contexto de build — Docker no puede copiar archivos ubicados fuera de él.

## 4. Construcción del Dockerfile — Etapa `builder`

Se crea un archivo llamado exactamente `Dockerfile`, sin extensión, en la raíz del contexto de build (`~/docker/api_som`). Docker busca ese nombre por defecto al ejecutar `docker build .`; usar otro nombre requeriría indicarlo explícitamente con la flag `-f`.

La primera etapa del archivo, llamada `builder`, tiene como único propósito instalar las dependencias del proyecto dentro de un entorno virtual de Python, de forma aislada del resto del sistema de archivos.

### 4.1 Imagen base de la etapa

```dockerfile
FROM python:3.12-slim AS builder
```

- `FROM python:3.12-slim` — Define la imagen base sobre la que se construye esta etapa. `python:3.12-slim` es una variante reducida de la imagen oficial de Python: incluye el intérprete y lo mínimo del sistema operativo base (Debian) necesario para que funcione, sin herramientas de compilación ni paquetes adicionales que sí trae la imagen `python:3.12` completa.
- `AS builder` — Asigna un alias a esta etapa del build. En un Dockerfile multi-stage, cada instrucción `FROM` inicia una etapa nueva; el alias permite referenciarla más adelante (en este caso, con `COPY --from=builder` en la etapa final).

### 4.2 Crear el entorno virtual

```dockerfile
RUN python -m venv /opt/venv
```

- `RUN` — Ejecuta un comando dentro de la imagen durante el build. El resultado (los cambios en el sistema de archivos) queda grabado como una nueva capa de la imagen.
- `python -m venv /opt/venv` — Invoca el módulo `venv` de la biblioteca estándar de Python y le indica que cree el entorno virtual en la ruta `/opt/venv`. El módulo genera ahí una estructura completa: un intérprete propio (normalmente un enlace simbólico al Python base), la carpeta `bin/` con los ejecutables (`python`, `pip`), y `lib/`, donde se instalarán los paquetes.

Esta instrucción no depende de ningún archivo del proyecto, por lo que Docker la cachea de forma independiente: aunque cambien `requirements.txt` o el código de la aplicación en builds posteriores, esta capa no se vuelve a ejecutar.

### 4.3 Definir el directorio de trabajo

```dockerfile
WORKDIR /build
```

- `WORKDIR` — Establece el directorio de trabajo dentro de la imagen para todas las instrucciones siguientes (`COPY`, `RUN`, etc.), hasta que se defina otro `WORKDIR`. Si el directorio no existe, Docker lo crea automáticamente.
- `/build` — Ruta arbitraria, fuera de cualquier carpeta reservada del sistema, usada por convención para alojar el código fuente durante el proceso de compilación. No tiene relación con `/opt/venv`, que es donde vive el entorno virtual.

Una vez definido `WORKDIR /build`, las instrucciones siguientes pueden usar rutas relativas: por ejemplo, `COPY requirements.txt .` copia el archivo a `/build/requirements.txt`.

### 4.4 Copiar `requirements.txt`

```dockerfile
COPY requirements.txt .
```

- `COPY <origen> <destino>` — Copia archivos desde el contexto de build (el sistema anfitrión) hacia el sistema de archivos de la imagen.
- `requirements.txt` — Origen: el archivo tal como está en el directorio del proyecto.
- `.` — Destino: el directorio actual dentro de la imagen (`/build`, por el `WORKDIR` anterior).

Esta instrucción se ejecuta **antes** de copiar el código de la aplicación, siguiendo el orden de capas recomendado para aprovechar la caché de Docker. Docker cachea cada instrucción por separado: si primero se copia `requirements.txt` y se instalan las dependencias, y luego se copia el código de la aplicación, un cambio posterior en el código no invalida la capa de instalación de dependencias — Docker la reutiliza desde caché porque `requirements.txt` no cambió. Si se copiara todo el proyecto en un solo `COPY`, cualquier cambio en el código forzaría reinstalar todas las dependencias en cada build.

### 4.5 Instalar dependencias

```dockerfile
RUN /opt/venv/bin/pip install -r requirements.txt
```

- `/opt/venv/bin/pip` — Ruta completa al `pip` que vive dentro del entorno virtual creado en el paso 4.2. Al invocarlo por ruta explícita, en vez de solo `pip`, se garantiza que los paquetes se instalen dentro de `/opt/venv/lib/...` y no en el `pip` del sistema, sin depender de que el entorno virtual esté activado.
- `install -r requirements.txt` — La flag `-r` indica a `pip` que lea la lista de paquetes desde un archivo, en vez de recibirlos como argumentos individuales. Como el `WORKDIR` sigue siendo `/build`, la ruta se resuelve a `/build/requirements.txt`.

Con esta instrucción, la etapa `builder` queda completa: existe un entorno virtual en `/opt/venv` con todas las dependencias instaladas, listo para que la etapa final lo copie.

### Nota sobre `pip install --user` frente a entorno virtual

Antes de definir este enfoque se evaluó la alternativa de usar `pip install --user`, que instala los paquetes en `$HOME/.local/lib/pythonX.Y/site-packages`. Esa ruta depende del usuario que ejecuta el comando: en la etapa `builder`, si no se define un usuario no-root ahí también, el proceso corre como `root` y los paquetes quedan en `/root/.local`. Al copiar ese directorio hacia la etapa final, donde el proceso corre como usuario no-root, sería necesario moverlo al `$HOME` de ese usuario y ajustar el propietario con `--chown`, coordinando explícitamente `HOME` y UID entre ambas etapas.

El entorno virtual en una ruta fija (`/opt/venv`), en cambio, no depende de qué usuario ejecuta `pip install` ni de qué usuario esté activo en la etapa final: basta con copiar el directorio completo y agregar `/opt/venv/bin` al `PATH`. Esto elimina la dependencia entre usuario y ubicación de paquetes, y además ilustra con mayor claridad el patrón multi-stage, ya que lo que cruza de una etapa a otra es un artefacto autocontenido.

## 5. Construcción del Dockerfile — Etapa final

La segunda etapa del archivo construye la imagen que efectivamente se va a ejecutar. Arranca desde una imagen base limpia — no hereda nada de lo instalado en `builder`, salvo lo que se copie explícitamente.

### 5.1 Imagen base de la etapa final

```dockerfile
FROM python:3.12-slim
```

Misma imagen base reducida usada en `builder`. A diferencia del primer `FROM`, esta instrucción no lleva alias (`AS <nombre>`), porque es la última etapa del archivo y ninguna otra etapa la va a referenciar con `COPY --from=`.

Este es el punto central del patrón multi-stage: la etapa final arranca desde cero, sin cachés de `pip`, archivos temporales ni nada de lo que se generó en `builder`. Lo único que se trae de esa etapa es el directorio `/opt/venv`, copiado explícitamente más adelante. Todo lo demás se descarta al terminar el build, lo que reduce el tamaño y la superficie de la imagen final.

### 5.2 Directorio de trabajo

```dockerfile
WORKDIR /app
```

Define el directorio de trabajo para las instrucciones siguientes en esta etapa. Si `/app` no existe en la imagen base, Docker lo crea automáticamente. Se usa una ruta distinta a `/build` (la de `builder`) porque cumple un propósito distinto: `/app` es la convención para el directorio donde vive el código de la aplicación en ejecución, mientras que `/build` era solo un espacio temporal de compilación descartado junto con esa etapa.

### 5.3 Crear el usuario no-root

```dockerfile
RUN useradd --uid 1000 --create-home appuser
```

- `useradd` — Comando estándar de Linux (disponible en la imagen base, que es Debian) para crear una cuenta de usuario en el sistema de archivos de la imagen.
- `--uid 1000` — Fija explícitamente el UID (identificador numérico de usuario) en `1000`, en vez de dejar que el sistema asigne el siguiente disponible. Un UID fijo hace el contenedor reproducible y auditable — algo relevante para políticas de seguridad que restringen contenedores corriendo como `root` (UID 0) o que validan UIDs específicos.
- `--create-home` — Crea el directorio home del usuario (`/home/appuser`). No es indispensable para que la aplicación funcione, ya que el código vive en `/app`, pero evita advertencias de herramientas que esperan un `$HOME` válido y mantiene el sistema de archivos coherente.
- `appuser` — Nombre de la cuenta.

Esta instrucción crea el usuario, pero no lo activa todavía: el build sigue corriendo como `root` hasta la instrucción `USER` (paso 5.10). Esto es intencional, ya que los pasos siguientes necesitan privilegios de `root` para escribir en el sistema de archivos y asignar propietarios.

### 5.4 Asignar propietario al directorio de trabajo

```dockerfile
RUN chown appuser:appuser /app
```

Esta instrucción cambia el propietario del directorio `/app` (creado en el paso 5.2) de `root:root` a `appuser:appuser`.

Es necesaria porque `WORKDIR /app` crea el directorio mientras el build todavía corre como `root`, y una instrucción `COPY --chown` posterior (ver 5.6) solo asigna propietario al **contenido** que copia, no al directorio contenedor si este ya existía de antes. Sin este `chown`, el directorio `/app` permanece como `root:root`, y en tiempo de ejecución, el proceso corriendo como `appuser` no tiene permiso de escritura sobre `/app` — necesario, por ejemplo, para crear el archivo de log de la aplicación, que no existe en la imagen y se genera recién en la primera escritura. Esta corrección se identificó durante las pruebas del contenedor y se documenta en detalle en la sección 9.1 (Troubleshooting).

Esta instrucción debe ubicarse después de que el usuario exista (5.3) y antes de cambiar a ese usuario con `USER` (5.10).

### 5.5 Copiar el entorno virtual desde `builder`

```dockerfile
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
```

- `COPY --from=builder` — En vez de copiar desde el contexto de build local, indica a Docker que copie desde el sistema de archivos de la etapa `builder`, usando el alias definido en el primer `FROM`. Docker no busca una imagen llamada `builder` en el sistema (no aparece en `docker images`); la etapa intermedia se mantiene en una caché interna, identificada por su alias, mientras dura el build en curso.
- `--chown=appuser:appuser` — Asigna como propietario del contenido copiado al usuario `appuser` y su grupo (`useradd` crea por defecto un grupo con el mismo nombre que el usuario). Sin esta flag, los archivos copiados mantendrían el propietario original de la etapa `builder`, que es `root` — y el proceso final, corriendo como `appuser`, necesita poder leer y ejecutar los binarios del entorno virtual (`python`, `pip`).
- `/opt/venv /opt/venv` — Origen y destino. Se copia el directorio completo desde la misma ruta en `builder` hacia la misma ruta en la etapa final. Usar la misma ruta en ambos lados no es obligatorio, pero evita confusión.

### 5.6 Ajustar el `PATH`

```dockerfile
ENV PATH="/opt/venv/bin:$PATH"
```

- `ENV` — Define una variable de entorno que queda grabada en la imagen y persiste tanto en instrucciones posteriores del build como en el contenedor en ejecución. Esto la distingue de una activación de entorno virtual con `source .../activate` dentro de una instrucción `RUN`: cada `RUN` se ejecuta en un shell nuevo e independiente que no hereda el estado de instrucciones anteriores, por lo que una activación así desaparecería al terminar esa instrucción.
- `PATH="/opt/venv/bin:$PATH"` — Reconstruye la variable `PATH` anteponiendo `/opt/venv/bin` al valor heredado de la imagen base. El shell busca ejecutables en el orden en que aparecen las rutas dentro de `PATH`, de izquierda a derecha; al quedar primero, cualquier comando `python` o `pip` invocado sin ruta completa se resuelve contra los binarios del entorno virtual antes que contra los del sistema.

Gracias a esta instrucción, la instrucción `CMD` final (5.11) puede invocar simplemente `python`, sin necesidad de escribir la ruta completa cada vez.

### 5.7 Copiar el código de la aplicación

```dockerfile
COPY --chown=appuser:appuser som_api_demo.py .
```

- `COPY` (sin `--from`) — El origen es el contexto de build local, no otra etapa.
- `--chown=appuser:appuser` — Mismo motivo que en 5.5: sin esta flag, el archivo quedaría con propietario `root`.
- `som_api_demo.py .` — Origen y destino. El archivo queda en `/app/som_api_demo.py`, gracias al `WORKDIR /app` definido en 5.2.

Esta instrucción se ubica después de copiar el entorno virtual (5.5), siguiendo el mismo principio de caché aplicado en la etapa `builder`. El código de la aplicación es el archivo con mayor probabilidad de cambiar durante el desarrollo; si cambia, Docker invalida la caché a partir de esta instrucción en adelante, pero la capa del entorno virtual (la más pesada, con todas las dependencias) permanece en caché y no se reconstruye en cada build.

### 5.8 Definir el puerto

```dockerfile
ENV PORT=8081
```

Define la variable de entorno `PORT` dentro de la imagen, con valor por defecto `8081`. Al quedar declarada con `ENV`, forma parte de la imagen: si el contenedor se ejecuta sin especificar `-e PORT=...`, la aplicación de todas formas encuentra un valor.

El efecto real ocurre en conjunto con el cambio de código aplicado en el prerrequisito:

```python
PORT = int(os.environ.get("PORT", 8081))
```

Esta línea lee la variable de entorno `PORT` si existe (la definida aquí con `ENV`, o la que se pase en tiempo de ejecución con `docker run -e PORT=9000 ...`), y usa `8081` como respaldo si no existe. El `ENV PORT=8081` del Dockerfile y el `8081` del código cumplen roles complementarios: el primero fija el valor dentro de la imagen; el segundo es una salvaguarda en caso de que la aplicación se ejecute en un contexto donde la variable de entorno no esté definida en absoluto.

### 5.9 Forzar salida sin buffer (`PYTHONUNBUFFERED`)

```dockerfile
ENV PYTHONUNBUFFERED=1
```

Esta instrucción no formaba parte de la primera versión del `Dockerfile`. Se agregó después de observar, en la validación del contenedor (sección 9.2), que las líneas propias de registro (`registrar()` / `print()`) no aparecían en tiempo real, a diferencia del log de acceso de Werkzeug.

La causa es un comportamiento del intérprete de Python, no de Docker: cuando `stdout` no está conectado a una terminal interactiva (TTY) — que es la situación normal de un contenedor en primer plano —, Python usa buffering **por bloque**: acumula la salida en un buffer interno y solo la escribe cuando el buffer se llena o el proceso termina. `stderr`, en cambio, es no-bufereado (o bufereado por línea, según la versión) por defecto, independiente de si hay TTY o no.

Werkzeug (el servidor de desarrollo que usa Flask) escribe su log de acceso en `stderr`, por lo que ese log siempre se ve en tiempo real. La función propia `registrar()` de este proyecto usa `print()`, que escribe en `stdout` — y por eso, sin esta variable, sus líneas quedaban retenidas en el buffer hasta que el proceso recibía una señal de término (`Ctrl+C` / `SIGINT`) y el buffer se vaciaba de golpe.

`PYTHONUNBUFFERED=1` fuerza a Python a tratar `stdout` y `stderr` como no-bufereados, sin importar si hay TTY o no. Con esto, ambas fuentes de log aparecen en tiempo real y en el orden real en que ocurren los eventos — relevante para cualquier registro que un motor de contenedores u orquestador vaya a recolectar en tiempo real (`docker logs -f`, o el equivalente en Kubernetes).

Esta instrucción se ubica junto a `ENV PORT=8081` (5.8), antes de `USER appuser` (5.10) — el orden entre ambas `ENV` no es significativo, pero agruparlas mantiene juntas las variables de entorno de la aplicación.

### 5.10 Cambiar al usuario no-root

```dockerfile
USER appuser
```

A partir de esta instrucción, todo lo que ocurra después —incluido el proceso que arranca con `CMD`— se ejecuta con la identidad de `appuser` (UID 1000), no como `root`.

Esta instrucción se ubica después de todas las operaciones de copia y asignación de propietario, y antes de `EXPOSE`/`CMD`. Si se cambiara a `appuser` antes de esas operaciones, fallarían por falta de permisos para escribir en `/opt/venv` o `/app`. Al dejar `USER appuser` para el final del build, se aprovechan los privilegios de `root` durante todo el proceso de construcción de la imagen, y se restringe el privilegio únicamente en el momento de ejecución del contenedor — que es el objetivo de seguridad de esta decisión de diseño.

### 5.11 Puerto expuesto y comando de arranque

```dockerfile
EXPOSE $PORT

CMD ["python", "som_api_demo.py"]
```

- `EXPOSE $PORT` — Documenta, como metadato de la imagen, en qué puerto espera tráfico el proceso dentro del contenedor. Es puramente informativo: no publica el puerto hacia la red ni hacia el host; eso ocurre en tiempo de ejecución con la flag `-p` de `docker run`. Se usa `$PORT` en vez de escribir `8081` directamente porque Docker expande variables de entorno definidas previamente con `ENV` en el mismo archivo.
- `CMD ["python", "som_api_demo.py"]` — Define el comando que se ejecuta al arrancar el contenedor (no durante el build). Está escrito en **forma exec** (arreglo JSON), no en forma shell (`CMD python som_api_demo.py`):
  - En forma exec, `python` se ejecuta directamente como el proceso principal del contenedor (PID 1), sin un shell intermedio.
  - En forma shell, Docker antepone automáticamente `/bin/sh -c`, por lo que el shell se convierte en PID 1 y el proceso Python queda como hijo.
  - Esto afecta cómo el contenedor recibe señales de apagado (por ejemplo, `SIGTERM` al ejecutar `docker stop`): en forma exec, la señal llega directo al proceso Python, que puede manejarla y cerrar limpiamente; en forma shell, el shell intermedio puede no reenviarla correctamente, provocando que el contenedor espere el timeout completo antes de ser terminado a la fuerza (`SIGKILL`).
  - `python`, sin ruta completa, se resuelve contra `/opt/venv/bin/python` gracias al `ENV PATH` definido en 5.6 — por lo tanto corre con el intérprete y las dependencias del entorno virtual, no con el Python base de la imagen.

## 6. Dockerfile completo

```dockerfile
# Etapa builder: instala dependencias en un entorno virtual aislado
FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv

WORKDIR /build

COPY requirements.txt .

RUN /opt/venv/bin/pip install -r requirements.txt


# Etapa final: imagen limpia que ejecuta la aplicación como usuario no-root
FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 1000 --create-home appuser

RUN chown appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser som_api_demo.py .

ENV PORT=8081
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE $PORT

CMD ["python", "som_api_demo.py"]
```

## 7. Build de la imagen

Desde el directorio de trabajo (`~/docker/api_som`), donde se encuentran el `Dockerfile`, `som_api_demo.py` y `requirements.txt`:

```bash
docker build -t som-api-demo .
```

- `docker build` — Lee el `Dockerfile` en el directorio indicado y ejecuta, en orden, cada instrucción de ambas etapas.
- `-t som-api-demo` — Asigna un nombre (tag) a la imagen resultante. Sin esta flag, la imagen se crea sin nombre, identificable solo por su ID hash.
- `.` — El contexto de build: le indica a Docker que use el directorio actual como raíz para resolver las instrucciones `COPY`.

### Interpretación de la salida

Docker (con BuildKit, el motor de build por defecto en versiones recientes) analiza las dependencias reales entre etapas, no solo el orden textual del archivo. Las instrucciones de la etapa final que no dependen de nada producido por `builder` —como `WORKDIR /app`, `RUN useradd` o `RUN chown`— pueden ejecutarse en paralelo con los pasos de `builder`, aprovechando los núcleos disponibles del sistema anfitrión. Por eso, en la salida del build es normal ver los pasos de ambas etapas entrelazados (identificados como `[builder N/M]` y `[stage-1 N/M]`) en vez de un orden estrictamente secuencial. La sincronización ocurre recién en la instrucción `COPY --from=builder`, que sí espera a que la etapa `builder` termine antes de poder copiar el entorno virtual. El resultado final de la imagen es idéntico al que se obtendría con ejecución estrictamente secuencial; solo cambia el tiempo total de build.

Cada instrucción aparece marcada como `CACHED` cuando Docker reutiliza una capa de un build anterior sin volver a ejecutarla. En un build limpio (primera vez), no aparece ningún `CACHED`.

### Errores más comunes en un primer intento

- `COPY` fallando porque `requirements.txt` o `som_api_demo.py` no están en el mismo directorio que el `Dockerfile`.
- Errores de sintaxis en alguna instrucción (paréntesis, comillas, espacios o barras `/` mal puestas), que Docker reporta indicando el número de línea del `Dockerfile`.
- Errores dentro de `pip install` si algún paquete de `requirements.txt` está mal escrito o no existe en el índice de paquetes.

## 8. Validación de la imagen

### 8.1 Confirmar que la imagen existe

```bash
docker images som-api-demo
```

Lista la imagen con su nombre (`REPOSITORY`), tag (`TAG`, `latest` por defecto si no se especificó uno explícito), `IMAGE ID` (los primeros caracteres del hash `sha256` mostrado al final del build) y tamaño.

### 8.2 Ejecutar el contenedor

```bash
docker run -p 8081:8081 som-api-demo
```

- `-p 8081:8081` — Publica el puerto `8081` del contenedor hacia el puerto `8081` del sistema anfitrión, en formato `host:contenedor`.

### 8.3 Probar los endpoints

En otra terminal, con el contenedor corriendo:

```bash
curl http://localhost:8081/api/v1/ordenes
```

Para probar creación y eliminación de recursos (ajustando el cuerpo de la petición según el contrato de la API):

```bash
curl -X POST http://localhost:8081/api/v1/ordenes -H "Content-Type: application/json" -d '{...}'
curl -X DELETE http://localhost:8081/api/v1/ordenes/<id>
```

Una respuesta `201` en la creación y `200` en el listado confirma que la aplicación responde correctamente dentro del contenedor.

### 8.4 Verificar que el proceso corre como usuario no-root

Con el contenedor corriendo (en otra terminal, o agregando `-d` al `docker run` de 8.2):

```bash
docker top <nombre_o_id_del_contenedor>
```

`docker top` lista los procesos del contenedor tal como los ve el sistema anfitrión, incluyendo la columna `UID`. El resultado esperado es que el proceso `python som_api_demo.py` aparezca con UID `1000` (o el nombre `appuser`, según cómo el anfitrión resuelva ese UID), no `root` ni `0` — confirmando en tiempo de ejecución lo que la instrucción `USER appuser` (5.10) declara en el `Dockerfile`.

*Pendiente: ejecutar y registrar aquí la salida real de este comando.*

### 8.5 Verificar el override de `PORT` en tiempo de ejecución

```bash
docker run -p 9090:9090 -e PORT=9090 som-api-demo
```

- `-e PORT=9090` — Sobrescribe, solo para este contenedor, la variable de entorno `PORT` definida en la imagen (`ENV PORT=8081`, sección 5.8). El código (`PORT = int(os.environ.get("PORT", 8081))`) toma este valor en tiempo de ejecución.
- `-p 9090:9090` — Debe coincidir con el nuevo puerto interno, ya que la publicación de puertos mapea el puerto real en el que escucha el proceso dentro del contenedor.

Una llamada exitosa a `curl http://localhost:9090/api/v1/ordenes` confirma que el mecanismo de configuración por variable de entorno funciona sin reconstruir la imagen.

*Pendiente: ejecutar y registrar aquí la salida real de esta prueba.*

### 8.6 Dónde queda almacenada la imagen

Docker no guarda la imagen como un archivo suelto en el sistema de archivos del anfitrión. La almacena en su propio almacén interno de imágenes, gestionado por el daemon de Docker (en Linux, normalmente bajo `/var/lib/docker`, aunque esa ruta no debe manipularse directamente). El acceso y la gestión se realizan exclusivamente a través de comandos `docker`.

## 9. Troubleshooting — casos reales documentados

### 9.1 Permisos de escritura en `/app`

Durante la validación del contenedor se presentó el siguiente error al ejecutar operaciones que escriben en el log de la aplicación (`POST`, `DELETE`):

```
PermissionError: [Errno 13] Permission denied: 'som_api_demo.log'
```

**Diagnóstico**

```bash
docker run --rm som-api-demo ls -la /app
```

Salida obtenida:

```
drwxr-xr-x 1 root    root     4096 Sep 16 23:16 .
drwxr-xr-x 1 root    root     4096 Sep 16 23:23 ..
-rw-r--r-- 1 appuser appuser 13666 Sep 16 21:43 som_api_demo.py
```

Esto confirma la causa raíz: el directorio `/app` tenía propietario `root:root`, mientras que el archivo `som_api_demo.py` dentro de él tenía propietario `appuser:appuser`.

**Causa raíz**

`COPY --chown` asigna propietario únicamente al contenido que copia en esa instrucción — no modifica el propietario del directorio contenedor si este ya existía de antes. La secuencia original del Dockerfile era:

1. `WORKDIR /app` crea el directorio mientras el build corre como `root` (todavía no se había ejecutado `USER appuser`), por lo que `/app` queda con propietario `root:root`.
2. `COPY --chown=appuser:appuser som_api_demo.py .` asigna `appuser` como propietario del archivo copiado, pero no del directorio `/app` en sí.

En Linux, para crear un archivo nuevo dentro de un directorio se requiere permiso de escritura sobre ese directorio, no solo sobre archivos individuales que ya existan ahí. El archivo `som_api_demo.log` no existe en la imagen — se crea recién en tiempo de ejecución, en la primera llamada a `open(LOG_FILE, "a", ...)`. Como el proceso corre como `appuser` (no propietario ni root) y `/app` tiene permisos `755` (sin escritura para "otros"), el kernel deniega la operación.

El build no falla por este motivo, porque nada durante el proceso de build intenta escribir en `/app` como `appuser`. El problema se manifiesta únicamente en tiempo de ejecución.

**Corrección aplicada**

```dockerfile
RUN chown appuser:appuser /app
```

Insertada después de `RUN useradd ...` y antes de `COPY --from=builder ...`, en el punto donde tanto el directorio como el usuario ya existen y el build todavía corre como `root` (ver sección 5.4).

Tras reconstruir la imagen, las mismas operaciones (`POST`, `DELETE`) respondieron correctamente (`201`, `404` según corresponda), confirmando la corrección.

### 9.2 Buffering de `stdout` en el log propio de la aplicación

Con el contenedor corriendo en primer plano (`docker run -p 8081:8081 som-api-demo`, sin `-d`), se observó una diferencia de comportamiento entre dos fuentes de log que debieran verse ambas en tiempo real:

- El log de acceso de Werkzeug (una línea por cada solicitud HTTP recibida) aparecía de inmediato, apenas se ejecutaba cada `curl`.
- Las líneas generadas por la función propia `registrar()` (que usa `print()`) no aparecían en absoluto durante la ejecución — solo se mostraban todas juntas, de golpe, al detener el contenedor con `Ctrl+C`.

**Diagnóstico**

Ambas fuentes de log escriben a flujos distintos del proceso: Werkzeug escribe en `stderr`; `registrar()` escribe en `stdout` mediante `print()`. Python aplica una política de buffering distinta a cada flujo cuando el proceso no está conectado a una terminal interactiva (TTY) — la situación normal de un contenedor:

- `stderr` es no-bufereado (o bufereado por línea) por defecto, sin importar si hay TTY.
- `stdout` se bufferea **por bloque** cuando no hay TTY: la salida se acumula en memoria y solo se escribe cuando el buffer se llena o el proceso termina.

Al recibir `Ctrl+C` (`SIGINT`), el proceso termina y el buffer de `stdout` se vacía de una sola vez — de ahí que todas las líneas de `registrar()` aparecieran juntas recién en ese momento, y no en el orden real en que ocurrieron los eventos que registraban.

**Causa raíz**

Ausencia de la variable de entorno `PYTHONUNBUFFERED` en la imagen. Sin ella, Python usa su política de buffering por defecto descrita arriba.

**Corrección aplicada**

```dockerfile
ENV PYTHONUNBUFFERED=1
```

Agregada junto a `ENV PORT=8081`, antes de `USER appuser` (ver sección 5.9). Esta variable fuerza a Python a tratar `stdout` (y `stderr`) como no-bufereados en cualquier condición, con o sin TTY.

*Pendiente: reconstruir la imagen con esta línea agregada y confirmar que las líneas de `registrar()` aparecen en tiempo real, en el mismo orden que las de Werkzeug.*

## 10. Publicación en Docker Hub

Docker Hub exige que el nombre de la imagen incluya el usuario de la cuenta, con el formato `usuario/repositorio:tag`.

### 10.1 Autenticación

```bash
docker login
```

Solicita usuario y contraseña (o un token de acceso, recomendado en vez de la contraseña de la cuenta) de Docker Hub.

### 10.2 Etiquetar la imagen

```bash
docker tag som-api-demo tu-usuario/som-api-demo:latest
```

`docker tag` no crea una copia física de la imagen — crea un alias adicional que apunta al mismo `IMAGE ID`. Ambos nombres son visibles con `docker images`.

### 10.3 Subir la imagen

```bash
docker push tu-usuario/som-api-demo:latest
```

Sube las capas de la imagen que aún no existen en Docker Hub. Las capas base de `python:3.12-slim` probablemente ya están cacheadas en el registro, por lo que normalmente solo se suben las capas propias del build (el entorno virtual y el código de la aplicación).

Reemplazar `tu-usuario` por el nombre de usuario real de la cuenta de Docker Hub.

## 11. Referencia — Instrucciones de Dockerfile

Esta sección funciona como glosario técnico. Cubre primero las instrucciones utilizadas en este ejercicio, y luego otras de uso común o recomendado que no se emplearon aquí, pero que conviene conocer.

### 11.1 Instrucciones utilizadas en este Dockerfile

**`FROM`** Define la imagen base de una etapa del build. Todo Dockerfile debe comenzar con al menos una instrucción `FROM`. En un build multi-stage, cada `FROM` inicia una etapa nueva e independiente; puede llevar un alias opcional (`AS <nombre>`) para ser referenciada por otras etapas.

**`RUN`** Ejecuta un comando durante el proceso de build, dentro del sistema de archivos de la imagen en construcción. El resultado queda grabado como una nueva capa. Se usa para instalar paquetes, crear usuarios, compilar código, o cualquier operación que deba quedar "horneada" en la imagen.

**`WORKDIR`** Establece el directorio de trabajo para las instrucciones siguientes (`RUN`, `COPY`, `CMD`, etc.). Si el directorio no existe, Docker lo crea. Permite usar rutas relativas en instrucciones posteriores y evita tener que repetir rutas absolutas.

**`COPY`** Copia archivos o directorios desde el contexto de build (el sistema anfitrión) hacia el sistema de archivos de la imagen. Con la flag `--from=<etapa>`, copia desde otra etapa del mismo build en vez del contexto local. Con `--chown=usuario:grupo`, asigna propietario al contenido copiado en la misma instrucción.

**`ENV`** Define una variable de entorno que queda grabada en la imagen. A diferencia de una variable exportada dentro de una instrucción `RUN` (que solo existe durante esa instrucción, ya que cada `RUN` corre en un shell nuevo), una variable definida con `ENV` persiste en instrucciones posteriores del build y en el contenedor cuando se ejecuta.

**`USER`** Define con qué usuario (y opcionalmente grupo) se ejecutan las instrucciones siguientes del build y, más importante, el proceso principal del contenedor en tiempo de ejecución. Por defecto, sin esta instrucción, todo corre como `root`.

**`EXPOSE`** Documenta, como metadato de la imagen, en qué puerto o puertos espera tráfico el proceso dentro del contenedor. Es informativo: no publica el puerto hacia el host ni hacia la red. La publicación real se controla en tiempo de ejecución con la flag `-p` de `docker run`.

**`CMD`** Define el comando que se ejecuta cuando arranca el contenedor. A diferencia de `RUN`, no se ejecuta durante el build, sino en cada `docker run`. Solo puede haber una instrucción `CMD` efectiva por imagen (si hay varias, solo la última tiene efecto). Puede escribirse en forma exec (`["ejecutable", "arg1", "arg2"]`, recomendada) o en forma shell (`ejecutable arg1 arg2`, que antepone `/bin/sh -c` automáticamente).

### 11.2 Otras instrucciones de uso común o recomendado

**`ADD`** Similar a `COPY`, pero con capacidades adicionales: puede extraer automáticamente archivos comprimidos locales (`.tar`, `.tar.gz`, etc.) hacia el destino, y puede descargar archivos desde una URL remota. Estas capacidades adicionales suelen considerarse un riesgo de claridad y seguridad (comportamiento implícito, descargas no verificadas), por lo que la recomendación general de la comunidad Docker es preferir `COPY` salvo que se necesite explícitamente la extracción automática de un archivo comprimido.

**`ARG`** Define una variable disponible únicamente durante el proceso de build, no en el contenedor en ejecución. Se declara con `ARG nombre=valor_por_defecto` y se puede sobrescribir en tiempo de build con `docker build --build-arg nombre=valor`. Se diferencia de `ENV` en que `ARG` no persiste en la imagen final ni es visible por el proceso en ejecución — es útil para parametrizar el build (por ejemplo, una versión de una dependencia) sin dejar ese valor grabado como variable de entorno del contenedor.

**`ENTRYPOINT`** Define el ejecutable principal del contenedor, de forma similar a `CMD`, pero con una diferencia clave de comportamiento: los argumentos pasados al ejecutar `docker run <imagen> <argumentos>` se agregan a `ENTRYPOINT` en vez de reemplazarlo por completo (que es lo que ocurre con `CMD`). Un patrón común es combinar ambas instrucciones: `ENTRYPOINT` define el binario fijo que siempre se ejecuta, y `CMD` define los argumentos por defecto, que sí pueden sobrescribirse desde la línea de comandos. Por ejemplo:

```dockerfile
ENTRYPOINT ["python", "som_api_demo.py"]
CMD ["--modo", "produccion"]
```

Con esta combinación, `docker run <imagen>` ejecuta `python som_api_demo.py --modo produccion`, mientras que `docker run <imagen> --modo debug` ejecuta `python som_api_demo.py --modo debug`, reemplazando solo la parte de `CMD`.

**`LABEL`** Agrega metadatos a la imagen en forma de pares clave-valor (por ejemplo, versión, mantenedor, información de licencia). No afecta el comportamiento del contenedor; sirve para documentación e integración con herramientas de gestión de imágenes.

**`VOLUME`** Declara un punto de montaje destinado a datos persistentes o compartidos, indicando que ese directorio dentro del contenedor no debe considerarse parte del sistema de archivos efímero de la capa de escritura. Si no se asocia explícitamente a un volumen o bind mount en `docker run`, Docker crea automáticamente un volumen anónimo. En este ejercicio no se usó, de forma deliberada, ya que el log de la aplicación se definió como efímero (desaparece con el contenedor).

**`HEALTHCHECK`** Define un comando que Docker ejecuta periódicamente dentro del contenedor para determinar si la aplicación está funcionando correctamente, más allá de si el proceso principal sigue vivo. El resultado se refleja en el estado del contenedor (visible con `docker ps`, como `healthy` o `unhealthy`), lo cual es especialmente útil en orquestadores que deciden si reiniciar o dejar de enrutar tráfico a un contenedor según ese estado.

**`STOPSIGNAL`** Define qué señal del sistema operativo se envía al proceso principal del contenedor cuando se ejecuta `docker stop`. Por defecto es `SIGTERM`. Se puede cambiar si la aplicación necesita manejar una señal distinta para un apagado ordenado.

**`ONBUILD`** Registra una instrucción que no se ejecuta en la imagen actual, sino que se dispara automáticamente cuando otra imagen usa esta como base (`FROM esta-imagen`). Se utiliza en imágenes pensadas explícitamente como plantillas base para otros proyectos. Es una instrucción de uso poco frecuente fuera de ese escenario específico.

**`SHELL`** Cambia el shell por defecto que Docker usa para ejecutar instrucciones en forma shell (`RUN`, `CMD`, `ENTRYPOINT` sin arreglo JSON). Por defecto es `["/bin/sh", "-c"]` en Linux. Se usa, por ejemplo, para cambiar a `bash` cuando se necesitan características específicas de ese shell.

## 12. Notas finales

Las siguientes decisiones de diseño del ejercicio son deliberadas, no descuidos, y responden al objetivo pedagógico de esta práctica:

- **Log efímero**: `som_api_demo.log` no se monta como volumen y desaparece junto con el contenedor. En un despliegue real, se optaría por un volumen, un bind mount, o el envío de logs a la salida estándar (`stdout`) para su recolección por el motor de contenedores u orquestador.
- **`API_KEY` fija en el código**: se mantiene como constante en `som_api_demo.py` en vez de pasarse como variable de entorno, por simplicidad pedagógica. En un despliegue real, un secreto de este tipo se gestionaría mediante variables de entorno inyectadas en tiempo de ejecución, o mediante un mecanismo de gestión de secretos (por ejemplo, Docker secrets o un Secret de Kubernetes).
- **Servidor de desarrollo de Flask**: la aplicación se ejecuta con el servidor de desarrollo integrado de Flask, que la propia salida del contenedor advierte como no apto para producción. Un despliegue real usaría un servidor WSGI de producción (por ejemplo, Gunicorn o uWSGI) detrás de la aplicación Flask.

Estas limitaciones no afectan la validez del ejercicio de contenerización en sí, que se centra en el patrón multi-stage build, la ejecución del proceso con un usuario no-root, y el comportamiento de buffering de E/S en un proceso sin TTY.