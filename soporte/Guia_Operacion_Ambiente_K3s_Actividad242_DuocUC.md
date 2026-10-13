> **CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana**
> Guía Paso a Paso — Operación del Ambiente Kubernetes (k3s) de la Actividad 2.4.2 (uso docente)

## 1. Información del Documento

| Campo | Valor |
| --- | --- |
| Documento | Guía Paso a Paso — Operación del Ambiente Kubernetes (k3s) de la Actividad 2.4.2 |
| Versión | 1.3 |
| Fecha | 13/10/2026 |
| Preparado por | Pablo Moscoso |
| Curso | CUY6142 — Telepresencia y Entornos Innovadores de Colaboración Humana |
| Actividad relacionada | 2.4.2 — reemplaza la *Guía Paso a Paso — Despliegue de SOM v2 y entorno de trabajo* |
| Destinatario | Docente (no se entrega a los estudiantes) |

### Gestión de Versiones

| Versión | Fecha | Preparado por | Sección y texto revisado |
| --- | --- | --- | --- |
| 1.0 | 08/10/2026 | Pablo Moscoso | Versión inicial. Ambiente preparado por el docente: clúster k3s de 1 servidor `t3.small` y 5 agentes `t3.medium`, un pod por estudiante (editor web y SOM v2.1), 20 cupos. Origen: en la clase del 05/10/2026 cerca del 90% de los estudiantes no completó la guía de despliegue. Memoria del editor medida el 08/10/2026 (~560 MiB por estudiante) |
| 1.1 | 09/10/2026 | Pablo Moscoso | (1) Paso 23 y Anexo 3-E: la tabla de credenciales entrega las URL completas con los nombres que usa la Actividad 2.4.2 v1.3 (`TU_URL_EDITOR`, `TU_URL_SOM`, `TU_URL_SWAGGER`), más la columna de Swagger. (2) Paso 24: la prueba de punta a punta sigue la Parte 0 de la actividad v1.3 |
| 1.2 | 13/10/2026 | Pablo Moscoso | (1) Nueva Sección 6.4: archivo de la sección (CSV con el RUT sin dígito verificador y el nombre); la contraseña del editor es el RUT con dígito verificador de cada estudiante (`claves <ARCHIVO_SECCION>`) y la tabla de acceso se publica en AVA sin contraseñas, con las contraseñas de los cupos de reserva en un archivo aparte (`tabla <ARCHIVO_SECCION>`). (2) Pasos 19 y 23, Secciones 6.1 a 6.3: referencias a la Sección 6.4. (3) Anexo 1: Problemas 7 y 9 actualizados y nuevo Problema 12 (errores del archivo de la sección). (4) Anexo 3-E: subcomandos nuevos. (5) `k8s/.gitignore` excluye el archivo de la sección y las tablas generadas |
| 1.3 | 13/10/2026 | Pablo Moscoso | (1) Nuevo Paso 6.4.2: cupo del docente (pod 20) con el RUT del docente como contraseña, configurado en `docente.env` (excluido del repositorio); no aparece en la tabla de acceso ni en las reservas. Los Pasos 6.4.2 a 6.4.6 pasan a ser 6.4.3 a 6.4.7. (2) Subcomando `docente`: aplica solo esa contraseña y reinicia solo el pod del docente. (3) Anexo 1, Problema 12, y Anexo 3-E actualizados |

---

## 2. Objetivo y Resultado Esperado

Al terminar esta guía tendrás, en el entorno de pruebas de AWS Academy, un ambiente listo para que cada estudiante haga la Actividad 2.4.2 **sin preparar nada**: abre una dirección en el navegador, escribe su contraseña y queda en un VS Code con todo instalado, conectado a su propio SOM.

| Componente | Qué es |
| --- | --- |
| Clúster k3s | 1 nodo servidor `t3.small` (solo administra el clúster) y 5 nodos agente `t3.medium` (ejecutan los ambientes) |
| Ambiente de cada estudiante | Un pod `est-N` (N de 1 a 20) con dos contenedores: el editor web (`code-server`) y SOM v2.1 |
| Acceso del estudiante | Editor en `http://<IP_PUBLICA_SERVIDOR>:301NN` y SOM (Postman y Swagger) en `http://<IP_PUBLICA_SERVIDOR>:302NN` |
| Datos del estudiante | Dos volúmenes propios: su carpeta personal (programas, Git, configuración) y los datos de su SOM |
| Contraseñas | Con el archivo de la sección (Sección 6.4), el RUT con dígito verificador de cada estudiante, y una al azar para los cupos de reserva. Sin archivo, una al azar por estudiante. Las genera el script `gestionar-ambiente.sh` |

**Qué recibe el estudiante, ya listo:**

- La carpeta `Formativa242` con `som_relocation.py`, `carga_masiva.py` y `listar_ordenes.py`.
- El entorno virtual `.venv` con `requests`, activo en cada terminal nueva (el indicador muestra `(.venv)`).
- Git con `credential.helper store`, `pull.rebase false` e `init.defaultBranch main`. El nombre y el correo los configura el estudiante.
- Ayuda para escribir Python: sangría de 4 espacios, guías de sangría visibles, autocompletado (extensión Python con el servidor de lenguaje Jedi) y errores de sintaxis e indentación subrayados en rojo mientras escribe (extensión Ruff).
- Su propio SOM, con datos que nadie más ve: los resultados esperados de la actividad (`com_id` `0000005`, suscripción `20000001`, 3 y 53 órdenes) se mantienen.

**Cómo se usa la guía.** Las Partes A a G se hacen una sola vez, para construir y validar el ambiente. La Sección 6 se repite en cada clase.

---

## 3. Requisitos Previos

- **Tu laptop** con Docker (o Podman), Git, `unzip` y acceso a internet. Ahí se construye la imagen del editor.
- **Cuenta de Docker Hub** `moscosov`, con permiso para publicar la imagen `moscosov/cuy6142-editor`.
- **Repositorio del curso** clonado en tu laptop (`som-api-demo`, rama `desarrollo`), con permiso para subir cambios.
- En la carpeta `scripts/` del repositorio: `som_relocation.py`, `carga_masiva.py` y `listar_ordenes.py`. La imagen los copia desde ahí.
- La imagen `moscosov/som-api-demo:v2.1` publicada en Docker Hub (verificado el 08/10/2026).
- El archivo `cuy6142-ambiente.zip` entregado junto con esta guía (carpetas `editor/` y `k8s/`).
- **Entorno de pruebas de AWS Academy** iniciado (Start Lab). Restricciones que esta guía respeta:
  - Tipos `t3.small` y `t3.medium` permitidos.
  - Máximo 9 instancias: esta guía usa 6. **Superar 9 suspende la cuenta del laboratorio**: termina antes las instancias que no uses.
  - Discos de hasta 35 GB y de tipo **gp2**.
  - Par de claves `vockey`.
- **PuTTY** con el archivo `labsuser.ppk` del laboratorio (botón **Details** → **Show** → **Download PPK**). PuTTY 0.75 o superior: las versiones anteriores no muestran el panel **Credentials**.

---

## 4. Datos de la Sesión

Completa esta tabla a medida que avanzas. Los valores entre `< >` de los pasos se reemplazan por estos datos.

| Dato | Valor | Se obtiene en |
| --- | --- | --- |
| `<RUTA_REPOSITORIO>` | [a completar] | Carpeta de tu laptop donde está clonado `som-api-demo` |
| `<RUTA_DEL_ZIP>` | [a completar] | Ruta del archivo `cuy6142-ambiente.zip` descargado |
| `<IP_PUBLICA_SERVIDOR>` | [a completar] | Paso 8. **Cambia cada vez que se reinicia el laboratorio.** Es la IP que usan los estudiantes |
| `<IP_PRIVADA_SERVIDOR>` | [a completar] | Paso 8. No cambia al detener y encender la instancia |
| `<VERSION_K3S>` | [a completar] | Paso 12 (por ejemplo `v1.34.1+k3s1`) |
| `<TOKEN_K3S>` | [a completar] | Paso 13. Texto largo que empieza con `K10` |
| `<IP_PUBLICA_AGENTE>` | [a completar] | Solo si debes entrar a un agente (Anexo 1) |
| `<RUT_DOCENTE>` | [a completar] | Paso 6.4.2. Tu RUT sin puntos ni dígito verificador. Se escribe solo en `docente.env`, en el servidor |
| `<ARCHIVO_SECCION>` | [a completar] | Sección 6.4. Archivo de la sección en `~/som-api-demo/k8s`, terminado en `.csv` (por ejemplo `seccion-D2.csv`) |
| `<NUMERO_ESTUDIANTE>` | — | Número del estudiante, de 1 a 20, sin ceros a la izquierda (`7`, no `07`) |

---

## 5. Procedimiento

### Parte A — Imagen del editor (en tu laptop)

La **imagen del editor** es la plantilla de la que nacen los 20 editores. Se construye una vez en tu laptop y se publica en Docker Hub; los agentes del clúster la descargan desde ahí.

#### Paso 1 — Agregar los archivos al repositorio

Entra a tu copia local del repositorio del curso:

```bash
cd <RUTA_REPOSITORIO>
```

> ⚠️ La ruta de abajo es un EJEMPLO — reemplázala por la carpeta donde clonaste `som-api-demo` (Sección 4).
>
> ❌ Incorrecto: `cd <~/som-api-demo>` (dejaste los símbolos < >)
> ✅ Correcto: `cd ~/som-api-demo` (tu ruta real, sin < >)

Cambia a la rama de trabajo del curso:

```bash
git switch desarrollo
```

Trae los últimos cambios de GitHub, por si la rama cambió desde otro equipo:

```bash
git pull
```

Descomprime el archivo entregado en la raíz del repositorio. Crea (o actualiza) las carpetas `editor/` y `k8s/`; `-d .` indica "descomprimir aquí":

```bash
unzip <RUTA_DEL_ZIP> -d .
```

> ⚠️ La ruta de abajo es un EJEMPLO — reemplázala por la ruta real del archivo descargado (Sección 4).
>
> ❌ Incorrecto: `unzip <~/Descargas/cuy6142-ambiente.zip> -d .` (dejaste los símbolos < >)
> ✅ Correcto: `unzip ~/Descargas/cuy6142-ambiente.zip -d .` (tu ruta real, sin < >)

Revisa que estén los archivos que la imagen necesita:

```bash
ls editor editor/plantilla k8s k8s/k3s scripts
```

Resultado esperado (el orden puede variar):

```text
editor:
Dockerfile  iniciar-editor.sh  plantilla  preparar-home.sh

editor/plantilla:
bashrc-cuy6142  gitconfig  settings.json

k8s:
00-namespace.yaml  20-estudiantes.yaml  gestionar-ambiente.sh  k3s

k8s/k3s:
agente-user-data.sh  servidor-config.yaml

scripts:
carga_masiva.py  listar_ordenes.py  som_relocation.py
```

Si en `scripts` faltan `carga_masiva.py` o `listar_ordenes.py`, agrégalos antes de seguir: sin ellos la construcción falla.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-1)

#### Paso 2 — Construir la imagen

Construye la imagen desde la **raíz** del repositorio (el punto final), porque el `Dockerfile` copia archivos de `scripts/`. `-f` indica dónde está el `Dockerfile` y `-t` el nombre y la etiqueta de la imagen:

```bash
docker build -f editor/Dockerfile -t moscosov/cuy6142-editor:v1 .
```

Tarda entre 3 y 6 minutos. Descarga `codercom/code-server:4.141.0-debian`, instala Python, las extensiones y los programas. En el registro de construcción, el paso `--list-extensions` debe mostrar estas cuatro líneas:

```text
charliermarsh.ruff@2026.84.0
ms-python.debugpy@2026.6.0
ms-python.python@2026.4.0
ms-python.vscode-python-envs@1.38.0
```

`debugpy` y `vscode-python-envs` se instalan solos: vienen en el paquete de la extensión Python. Pylance no se instala porque no está publicado en Open VSX (el repositorio de extensiones de `code-server`); por eso la configuración usa Jedi.

Si en vez de `ms-python.python` aparece la línea `AVISO: no se pudo instalar`, la imagen funciona igual, pero sin autocompletado: revisa el Problema 2.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-2)

#### Paso 3 — Probar la imagen en tu laptop

Antes de publicarla, comprueba que el editor arranca y pide la contraseña. Este paso simula lo que hace Kubernetes: entrega una contraseña como archivo y el nombre del pod como variable.

Crea una carpeta para la contraseña de prueba:

```bash
mkdir -p /tmp/claves-prueba
```

Escribe la contraseña de prueba `prueba123` en un archivo llamado como el pod (`est-1`):

```bash
printf 'prueba123' > /tmp/claves-prueba/est-1
```

Deja el archivo legible para el usuario del contenedor (en Kubernetes esto lo hace `fsGroup`):

```bash
chmod 0444 /tmp/claves-prueba/est-1
```

Ejecuta el editor. `--rm` borra el contenedor al detenerlo, `-p` publica el puerto 8080, `-e` define la variable `POD_NAME` y `-v` monta la carpeta de la contraseña en `/etc/claves`:

```bash
docker run --rm -p 8080:8080 -e POD_NAME=est-1 -v /tmp/claves-prueba:/etc/claves:ro moscosov/cuy6142-editor:v1
```

La terminal debe mostrar `Using password from $PASSWORD` y `HTTP server listening on http://0.0.0.0:8080/`. En el navegador de tu laptop abre la siguiente dirección y entra con `prueba123`:

```text
http://localhost:8080
```

Comprueba que:

1. El explorador muestra la carpeta `FORMATIVA242` con los tres programas.
2. Al abrir una terminal (menú **Terminal → New Terminal**), el indicador empieza con `(.venv)`.
3. Al abrir `listar_ordenes.py` y escribir una línea con mala sangría, aparece subrayada en rojo (Ruff). Deshaz el cambio con `Ctrl+Z`.

Los programas no logran conectarse a SOM en esta prueba: es normal, porque aquí SOM no está corriendo. Detén el editor con `Ctrl+C` en la terminal de tu laptop.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-3)

#### Paso 4 — Publicar la imagen en Docker Hub

Inicia sesión en Docker Hub con la cuenta `moscosov` (pide la contraseña o un token de acceso):

```bash
docker login
```

Sube la imagen. Pesa cerca de 1,7 GB sin comprimir; se sube comprimida y las capas de `code-server` se reutilizan si ya están en Docker Hub:

```bash
docker push moscosov/cuy6142-editor:v1
```

Resultado esperado (parte final): una línea `v1: digest: sha256:...`.

#### Paso 5 — Subir los archivos al repositorio

El servidor del clúster descarga los manifiestos y el script desde GitHub, así que deben quedar en la rama `desarrollo`.

Marca el script como ejecutable. Git guarda ese permiso, así que el servidor lo recibe listo para ejecutar:

```bash
chmod +x k8s/gestionar-ambiente.sh
```

Prepara las carpetas nuevas para el commit:

```bash
git add editor k8s
```

Crea el commit:

```bash
git commit -m "Ambiente k3s de la Actividad 2.4.2: imagen del editor, manifiestos y script"
```

Sube el commit a GitHub:

```bash
git push origin desarrollo
```

### Parte B — Red y servidor en AWS

#### Paso 6 — Iniciar el laboratorio y revisar las instancias

1. En AWS Academy, haz clic en **Start Lab** y espera la luz verde. Luego haz clic en **AWS** para abrir la consola.
2. En la consola, revisa que la región sea **us-east-1 (Norte de Virginia)**.
3. En **EC2 → Instancias**, cuenta las instancias que no están en estado **Terminada**. Con las 6 de esta guía, el total no puede superar 9. Termina las que no uses.

#### Paso 7 — Crear el grupo de seguridad

Un **grupo de seguridad** es el cortafuegos de las instancias: decide qué tráfico entra. Los 6 nodos usan el mismo.

1. **EC2 → Red y seguridad → Security Groups → Crear grupo de seguridad**.
2. **Nombre:** `k3s-cuy6142`. **Descripción:** `Cluster k3s Actividad 2.4.2`. **VPC:** la predeterminada.
3. Reglas de entrada:

| Tipo | Protocolo | Puertos | Origen | Descripción |
| --- | --- | --- | --- | --- |
| SSH | TCP | 22 | 0.0.0.0/0 | Acceso del docente con PuTTY |
| TCP personalizado | TCP | 30101-30120 | 0.0.0.0/0 | Editor de los estudiantes |
| TCP personalizado | TCP | 30201-30220 | 0.0.0.0/0 | SOM de los estudiantes |

4. Haz clic en **Crear grupo de seguridad**.
5. Ya creado, abre el grupo, pestaña **Reglas de entrada → Editar reglas de entrada → Agregar regla**:
   - **Tipo:** Todo el tráfico.
   - **Origen:** Personalizado, y elige el mismo grupo `k3s-cuy6142` (su ID empieza con `sg-`).
   - **Descripción:** `Trafico interno del cluster`.
6. **Guardar reglas**.

La última regla deja pasar todo el tráfico **entre los nodos del clúster** y nada desde afuera: la API de Kubernetes (6443/TCP), la red de los pods (flannel, 8472/UDP) y el kubelet (10250/TCP). Se agrega después de crear el grupo porque necesita su ID.

#### Paso 8 — Lanzar el nodo servidor

**EC2 → Instancias → Lanzar instancias**:

- **Nombre:** `k3s-servidor`.
- **AMI:** Ubuntu Server 24.04 LTS (HVM), SSD Volume Type, 64 bits (x86).
- **Tipo de instancia:** `t3.small`. El servidor solo administra el clúster: no ejecuta ambientes de estudiantes.
- **Par de claves:** `vockey`.
- **Configuración de red → Firewall:** Seleccionar un grupo de seguridad existente → `k3s-cuy6142`.
- **Configurar almacenamiento:** 20 GiB, tipo **gp2**. Cambia el tipo si aparece gp3: el entorno de pruebas solo permite gp2.

Haz clic en **Lanzar instancia**. Cuando esté **En ejecución**, selecciónala y anota en la Sección 4:

- **Dirección IPv4 pública** en `<IP_PUBLICA_SERVIDOR>`.
- **Direcciones IPv4 privadas** en `<IP_PRIVADA_SERVIDOR>`.

#### Paso 9 — Conectarse al servidor con PuTTY

1. Abre **PuTTY**. En **Connection**, escribe `30` en **Seconds between keepalives**, para que la sesión no se corte por inactividad.
2. En **Session → Host Name**, escribe lo siguiente. Puerto: `22`.

```text
ubuntu@<IP_PUBLICA_SERVIDOR>
```

> ⚠️ La IP de abajo es un EJEMPLO — reemplázala por la IP pública del servidor (Sección 4).
>
> ❌ Incorrecto: `ubuntu@<54.210.10.20>` (dejaste los símbolos < >)
> ❌ Incorrecto: `ec2-user@54.210.10.20` (ese usuario es de Amazon Linux; en Ubuntu es `ubuntu`)
> ✅ Correcto: `ubuntu@54.210.10.20` (la IP pública real, sin < >)

3. En **Connection → SSH → Auth → Credentials**, en **Private key file for authentication**, elige `labsuser.ppk`.
4. **Open**. La primera vez, acepta la huella del servidor con **Accept**.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-4)

### Parte C — Servidor de k3s

**k3s** es una distribución de Kubernetes liviana: un solo programa que incluye todo lo necesario. En el servidor corre el **plano de control** (la API de Kubernetes, el programador de pods y la base de datos del clúster).

#### Paso 10 — Clonar el repositorio del curso en el servidor

Ve a tu carpeta personal:

```bash
cd ~
```

Descarga la rama `desarrollo` del repositorio, que trae la configuración de k3s, los manifiestos y el script. `-b` elige la rama:

```bash
git clone -b desarrollo https://github.com/moscosov/som-api-demo.git
```

#### Paso 11 — Copiar la configuración de k3s

k3s lee su configuración desde `/etc/rancher/k3s/config.yaml` al instalarse y en cada arranque. Debe estar en su lugar **antes** de instalar.

Crea la carpeta de configuración. `-p` evita el error si ya existe:

```bash
sudo mkdir -p /etc/rancher/k3s
```

Copia la configuración del servidor desde el repositorio (contenido explicado en el Anexo 4-A):

```bash
sudo cp ~/som-api-demo/k8s/k3s/servidor-config.yaml /etc/rancher/k3s/config.yaml
```

#### Paso 12 — Instalar k3s en el servidor

Descarga el instalador oficial de k3s y lo ejecuta. Instala la última versión estable como servicio de `systemd` (`k3s.service`), que arranca solo cada vez que se enciende la instancia:

```bash
curl -sfL https://get.k3s.io | sh -
```

Tarda uno o dos minutos. Revisa el nodo:

```bash
kubectl get nodes
```

Resultado esperado (la versión puede variar):

```text
NAME               STATUS   ROLES           AGE   VERSION
ip-172-31-10-20    Ready    control-plane   40s   v1.34.1+k3s1
```

1. Anota la columna **VERSION** completa en `<VERSION_K3S>` (Sección 4). Los agentes deben instalar exactamente la misma versión.
2. La versión debe ser **1.31 o superior**: el StatefulSet numera los pods desde 1 con `spec.ordinals`, disponible desde esa versión.

Revisa que el servidor quedó con la restricción (taint) que impide ejecutar ahí ambientes de estudiantes:

```bash
kubectl describe node | grep Taints
```

Resultado esperado:

```text
Taints:             CriticalAddonsOnly=true:NoExecute
```

Revisa los componentes del sistema:

```bash
kubectl get pods -n kube-system
```

Deben aparecer `coredns`, `local-path-provisioner` y `metrics-server` en estado `Running`, y **no** deben aparecer `traefik` ni `svclb`: quedaron desactivados en la configuración.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-5)

#### Paso 13 — Obtener el token para unir los agentes

El **token** es la contraseña que un agente presenta para unirse al clúster. Muéstralo:

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

Copia la línea completa (empieza con `K10` y contiene `::server:`) en `<TOKEN_K3S>` (Sección 4).

Confirma la IP privada del servidor. La primera dirección que muestra este comando es la privada:

```bash
hostname -I
```

Debe coincidir con `<IP_PRIVADA_SERVIDOR>` (Paso 8).

### Parte D — Nodos agente

Los **agentes** ejecutan los pods de los estudiantes. Se lanzan los 5 a la vez con un script de **datos de usuario (user data)**: EC2 lo ejecuta como root en el primer arranque de cada instancia, y el script instala k3s en modo agente y lo une al servidor. Así no hay que entrar con PuTTY a cada agente.

#### Paso 14 — Preparar el script de datos de usuario

El script está en el repositorio, en `k8s/k3s/agente-user-data.sh`. Cópialo en un editor de texto de tu laptop (Kate o Typora) y reemplaza los tres valores entre `< >`:

```text
#!/bin/bash
export K3S_URL="https://<IP_PRIVADA_SERVIDOR>:6443"
export K3S_TOKEN="<TOKEN_K3S>"
export INSTALL_K3S_VERSION="<VERSION_K3S>"
curl -sfL https://get.k3s.io | sh -
```

> ⚠️ Los valores de abajo son EJEMPLOS — reemplázalos por los tuyos (Sección 4).
>
> ❌ Incorrecto: `K3S_URL="https://<172.31.10.20>:6443"` (dejaste los símbolos < >)
> ❌ Incorrecto: `K3S_URL="https://54.210.10.20:6443"` (es la IP pública; la pública cambia en cada sesión)
> ❌ Incorrecto: `INSTALL_K3S_VERSION="1.34.1"` (falta la `v` inicial y el sufijo `+k3s1`)
> ✅ Correcto: `K3S_URL="https://172.31.10.20:6443"`, `K3S_TOKEN="K10...::server:..."` e `INSTALL_K3S_VERSION="v1.34.1+k3s1"`

Se usa la **IP privada** porque no cambia al detener y encender las instancias: el clúster sigue unido entre sesiones del laboratorio.

#### Paso 15 — Lanzar los 5 agentes

**EC2 → Instancias → Lanzar instancias**:

- **Nombre:** `k3s-agente`.
- **AMI:** Ubuntu Server 24.04 LTS (HVM), SSD Volume Type, 64 bits (x86).
- **Tipo de instancia:** `t3.medium` (2 vCPU, 4 GiB). Cada agente aloja 4 estudiantes de unos 600 MiB cada uno.
- **Par de claves:** `vockey`.
- **Firewall:** grupo existente `k3s-cuy6142`.
- **Almacenamiento:** 20 GiB, tipo **gp2**.
- **Detalles avanzados → Datos de usuario:** pega el script del Paso 14, ya con tus valores.
- **Resumen (panel derecho) → Número de instancias:** `5`.

Haz clic en **Lanzar instancia**.

#### Paso 16 — Verificar que los agentes se unieron

Espera 3 minutos: cada agente arranca, descarga k3s y se une. En la terminal del servidor:

```bash
kubectl get nodes
```

Resultado esperado: 6 nodos en estado `Ready`, el servidor con el rol `control-plane` y los 5 agentes con `<none>`:

```text
NAME               STATUS   ROLES           AGE   VERSION
ip-172-31-10-20    Ready    control-plane   12m   v1.34.1+k3s1
ip-172-31-11-31    Ready    <none>          90s   v1.34.1+k3s1
ip-172-31-12-42    Ready    <none>          88s   v1.34.1+k3s1
ip-172-31-13-53    Ready    <none>          85s   v1.34.1+k3s1
ip-172-31-14-64    Ready    <none>          84s   v1.34.1+k3s1
ip-172-31-15-75    Ready    <none>          80s   v1.34.1+k3s1
```

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-6)

### Parte E — Desplegar el ambiente de los estudiantes

#### Paso 17 — Entrar a la carpeta de los manifiestos

Los comandos de esta parte y de la Sección 6 se ejecutan desde esta carpeta, porque el script guarda ahí la tabla de credenciales y los Services generados:

```bash
cd ~/som-api-demo/k8s
```

#### Paso 18 — Crear el espacio de nombres

Un **espacio de nombres (namespace)** agrupa los objetos del curso y los separa de los del sistema. Todo el ambiente vive en `cuy6142`:

```bash
kubectl apply -f 00-namespace.yaml
```

Resultado esperado: `namespace/cuy6142 created`.

#### Paso 19 — Generar las contraseñas

Crea el Secret `editor-claves`, con una contraseña al azar de 8 caracteres por estudiante:

```bash
./gestionar-ambiente.sh claves
```

Resultado esperado: `Secret editor-claves listo con 20 contrasenas.`

Si lo vuelves a ejecutar, conserva las contraseñas existentes. Para cambiarlas todas, ver la Sección 6.2.

Estas contraseñas al azar sirven para construir y validar el ambiente (Partes E a G). Para la clase, la Sección 6.4 reemplaza el Secret por las contraseñas de la sección: el RUT de cada estudiante.

#### Paso 20 — Crear los pods de los estudiantes

Aplica el manifiesto con el Service headless y el StatefulSet de 20 réplicas (explicado en el Anexo 4-G):

```bash
kubectl apply -f 20-estudiantes.yaml
```

Resultado esperado:

```text
service/est created
statefulset.apps/est created
```

Puede aparecer antes el aviso `Warning: spec.SessionAffinity is ignored for headless services`: es informativo.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-7)

#### Paso 21 — Crear los Services de acceso

Genera y aplica los 20 Services NodePort, uno por estudiante, con sus dos puertos (editor `301NN` y SOM `302NN`):

```bash
./gestionar-ambiente.sh servicios
```

Resultado esperado: 20 líneas `service/est-N created` y la ruta de `servicios-generados.yaml`.

Revisa los Services:

```bash
kubectl -n cuy6142 get svc
```

Cada `est-N` debe mostrar `8080:301NN/TCP,8081:302NN/TCP`. Por ejemplo, `est-7` muestra `8080:30107/TCP,8081:30207/TCP`.

#### Paso 22 — Esperar a que los ambientes estén listos

La primera vez, cada agente descarga la imagen del editor (cerca de 450 MB comprimida) y la de SOM: tarda entre 3 y 8 minutos. `watch` repite el comando cada 10 segundos:

```bash
watch -n 10 kubectl -n cuy6142 get pods -o wide
```

Los estados pasan por `Pending`, `Init:0/1` y `PodInitializing`. Cuando los 20 pods muestren `READY 2/2` y `STATUS Running`, sal con `Ctrl+C`. Revisa en la columna **NODE** que haya 4 pods por agente y ninguno en el servidor.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-8)

#### Paso 23 — Generar la tabla de credenciales

Genera la tabla con la IP pública actual del servidor. El script la obtiene del servicio de metadatos de EC2, así que no hay que escribirla:

```bash
./gestionar-ambiente.sh tabla
```

Resultado esperado (las contraseñas son al azar):

```text
| N | TU_URL_EDITOR (navegador) | TU_URL_SOM (solo Postman) | TU_URL_SWAGGER (navegador) | Contraseña |
| --- | --- | --- | --- | --- |
| 01 | http://54.210.10.20:30101 | http://54.210.10.20:30201/api/v2 | http://54.210.10.20:30201/api/v2/docs | xz2ntd9f |
```

Los nombres de las columnas son los mismos que usa la Actividad 2.4.2: cada estudiante copia los datos de su fila en la Sección 4 de la actividad.

Esta tabla, con contraseñas, es para la validación. Para la clase se publica la tabla de acceso de la Sección 6.4, sin contraseñas.

La tabla queda guardada en un archivo `credenciales-AAAAMMDD-HHMM.md` en la carpeta `k8s`. Para llevarla a tu laptop, selecciona el texto en la ventana de PuTTY (se copia solo) y pégalo en Typora.

### Parte F — Validación

#### Paso 24 — Probar el ambiente de un estudiante de punta a punta

Haz la prueba como estudiante 01, con la fila `01` de la tabla. Es lo mismo que hará cada estudiante en la Parte 0 de la actividad:

1. Abre su URL del editor en el navegador y entra con su contraseña.
2. Abre una terminal (**Terminal → New Terminal**): el indicador debe empezar con `(.venv)` y la carpeta debe ser `~/Formativa242`.
3. En la terminal, ejecuta `python listar_ordenes.py`. Debe responder `Total de ordenes: 0`: el editor llega a su SOM por `localhost`.
4. Abre `som_relocation.py`, escribe una línea con mala sangría y confirma que Ruff la subraya en rojo. Pasa el mouse sobre una palabra como `requests` para ver la ayuda de la extensión Python. Deshaz los cambios con `Ctrl+Z`.
5. Abre Swagger en el navegador: `http://<IP_PUBLICA_SERVIDOR>:30201/api/v2/docs`.
6. En Postman, haz el login con la variable `base` del estudiante 01 (`http://<IP_PUBLICA_SERVIDOR>:30201/api/v2`), usuario `gui` y contraseña `Cuy6142!`.

La sesión del editor se guarda en una cookie por dirección IP, no por puerto. Si en el mismo navegador entras a dos editores distintos, el segundo inicio de sesión reemplaza al primero: usa una ventana privada distinta para cada estudiante que pruebes.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-9)

#### Paso 25 — Medir la memoria con 4 estudiantes activos en un agente

El dimensionamiento (4 estudiantes por agente `t3.medium`) se basa en una medición de ~560 MiB por editor activo. Este paso lo confirma en el clúster real.

Muestra en qué nodo está cada pod:

```bash
kubectl -n cuy6142 get pods -o wide
```

Elige un agente y anota los 4 pods que tiene. Abre sus 4 editores (cada uno en su propia ventana privada), y en cada uno abre un archivo `.py` y una terminal. Espera un minuto y revisa la memoria de los pods, separada por contenedor:

```bash
kubectl -n cuy6142 top pods --containers
```

Revisa la memoria de los nodos:

```bash
kubectl top nodes
```

Criterio: en el agente elegido, la columna **MEMORY%** debe quedar bajo 85%. Si lo supera, revisa el Problema 10 antes de la clase.

#### Paso 26 — Prueba de carga

Ejecuta `carga_masiva.py` en los 20 ambientes **a la vez**: 1.000 órdenes en total, en paralelo. Es más carga que la de una clase real:

```bash
./gestionar-ambiente.sh prueba-carga
```

Resultado esperado: 20 líneas `Total de ordenes creadas: 50 de 50` y el tiempo total (debería ser menor a un minuto).

Revisa que ningún contenedor se haya reiniciado (columna **RESTARTS** en `0`) y el uso de memoria:

```bash
./gestionar-ambiente.sh estado
```

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-10)

### Parte G — Dejar el ambiente limpio para la clase

#### Paso 27 — Borrar los datos de prueba

Las pruebas dejaron órdenes en los SOM y cambios en las carpetas personales. Los estudiantes deben empezar con todo vacío: SOM sin órdenes, para que la Orden 1 obtenga la suscripción `20000001`.

Elimina el StatefulSet. Sus pods se detienen; los volúmenes, los Services y el Secret se conservan:

```bash
kubectl -n cuy6142 delete statefulset est
```

Elimina los volúmenes de todos los estudiantes, seleccionándolos por su etiqueta. Borra los datos de SOM y las carpetas personales:

```bash
kubectl -n cuy6142 delete pvc -l app.kubernetes.io/name=est
```

Crea de nuevo los pods. Nacen con volúmenes nuevos, copiados desde la plantilla de la imagen:

```bash
kubectl apply -f 20-estudiantes.yaml
```

Espera a que los 20 pods queden `2/2 Running` (esta vez es rápido: las imágenes ya están en los agentes):

```bash
watch -n 10 kubectl -n cuy6142 get pods
```

Las contraseñas no cambian: la tabla del Paso 23 sigue sirviendo mientras no cambie la IP.

#### Paso 28 — Revisar qué pasa al cerrar la sesión del laboratorio

Antes de la clase conviene saber cómo se comporta el entorno de pruebas al terminar la sesión:

1. Haz clic en **End Lab** (o deja que el contador llegue a cero).
2. Inicia de nuevo con **Start Lab** y abre la consola EC2.
3. Revisa el estado de las 6 instancias:
   - Si están **Detenidas**, inícialas (Sección 6.1, punto 2). Conservan sus discos: el clúster y los volúmenes siguen ahí.
   - Si están **Terminadas**, el entorno no conserva instancias entre sesiones: el ambiente se arma el mismo día de la clase (Partes B a G, sin la Parte A).

---

## 6. Operación Durante la Clase

### 6.1 Antes de la clase

1. **Start Lab** en AWS Academy y abre la consola EC2.
2. Si las instancias están **Detenidas**: selecciona las 6 → **Estado de la instancia → Iniciar instancia**.
3. Anota la nueva `<IP_PUBLICA_SERVIDOR>` (la IP privada no cambia) y conéctate con PuTTY (Paso 9).
4. Entra a la carpeta de los manifiestos:

```bash
cd ~/som-api-demo/k8s
```

5. Revisa nodos y pods. Tras encender las instancias, los agentes tardan uno o dos minutos en quedar `Ready` y los pods en volver a `2/2 Running`:

```bash
./gestionar-ambiente.sh estado
```

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-11)

6. Si la IP cambió, genera la tabla de acceso con la IP del día y publícala en AVA (Paso 6.4.6):

```bash
./gestionar-ambiente.sh tabla <ARCHIVO_SECCION>
```

### 6.2 Durante la clase

- **Renovar la sesión del laboratorio.** Antes de que el contador de AWS Academy llegue a cero, haz clic en **Start Lab** para renovarlo. Si la sesión termina, las instancias se detienen y los 20 ambientes se caen.

- **El editor de un estudiante no responde o se desconectó.** Reinicia su pod. Sus archivos y su SOM se conservan, porque están en sus volúmenes:

```bash
kubectl -n cuy6142 delete pod est-<NUMERO_ESTUDIANTE>
```

> ⚠️ El número de abajo es un EJEMPLO — reemplázalo por el número del estudiante en la tabla, sin ceros a la izquierda.
>
> ❌ Incorrecto: `kubectl -n cuy6142 delete pod est-<7>` (dejaste los símbolos < >)
> ❌ Incorrecto: `kubectl -n cuy6142 delete pod est-07` (el pod se llama `est-7`, sin cero)
> ✅ Correcto: `kubectl -n cuy6142 delete pod est-7`

- **Un estudiante necesita empezar de cero** (borró archivos, SOM quedó con datos equivocados). El script pide confirmación escribiendo `SI`, borra sus volúmenes y crea un pod nuevo:

```bash
./gestionar-ambiente.sh restablecer <NUMERO_ESTUDIANTE>
```

- **Un ambiente falla y no se recupera, o un estudiante no está en el archivo de la sección.** Entrégale un cupo de reserva (en la tabla dice `Reserva`) y su contraseña, del archivo `reservas-AAAAMMDD-HHMM.md` (Paso 6.4.6). Sigue con el ambiente dañado después de la clase.

- **Un estudiante no puede entrar con su RUT.** Revisa su fila en el archivo de la sección. Si el RUT está mal, corrígelo, repite el Paso 6.4.4 y reinicia solo su pod (Anexo 1, Problema 9).

- **Ver qué está recibiendo el SOM de un estudiante.** Muestra las últimas 20 líneas de su registro (cada solicitud con su código de respuesta):

```bash
kubectl -n cuy6142 logs est-<NUMERO_ESTUDIANTE> -c som --tail 20
```

- **Cambiar todas las contraseñas sin archivo de la sección.** Entre una sección y otra, usa en cambio la Sección 6.4. Genera contraseñas nuevas:

```bash
./gestionar-ambiente.sh claves --forzar
```

Reinicia los pods de a uno, para que los editores lean las contraseñas nuevas:

```bash
kubectl -n cuy6142 rollout restart statefulset est
```

Y genera la tabla nueva:

```bash
./gestionar-ambiente.sh tabla
```

### 6.3 Después de la clase

- Si otra sección usará el ambiente, prepáralo con la Sección 6.4: el Paso 6.4.5 borra el trabajo de los estudiantes, incluidos los tokens de GitHub que Git guardó en sus carpetas personales.
- Cierra la sesión con **End Lab**, o deja que el contador llegue a cero.

### 6.4 Preparar el ambiente para una sección (archivo de la sección)

Con el **archivo de la sección**, la contraseña del editor de cada estudiante es su RUT con dígito verificador, sin puntos ni guion y con la K en mayúscula (por ejemplo, `16123463K`). No hay contraseñas que repartir: el script calcula el dígito verificador (módulo 11) a partir del RUT sin dígito de la lista del curso. La tabla de acceso que se publica en AVA trae el nombre de cada estudiante y sus URL, sin contraseñas. Los cupos sin estudiante quedan de reserva, con una contraseña al azar que solo ve el docente, salvo el cupo 20, que es el del docente (Paso 6.4.2).

> ⚠️ **EL ARCHIVO DE LA SECCIÓN TIENE DATOS PERSONALES.**
>
> Se crea solo en el servidor del clúster, en la carpeta `k8s`. No se sube al repositorio ni se comparte: `k8s/.gitignore` excluye `*.csv`, `docente.env`, `tabla-acceso-*.md` y `reservas-*.md`.

Esta sección necesita la versión actual de `gestionar-ambiente.sh` (subcomandos `claves <ARCHIVO_SECCION>`, `tabla <ARCHIVO_SECCION>` y `docente`), subida a la rama `desarrollo` (Paso 5).

#### Paso 6.4.1 — Actualizar el repositorio en el servidor

Entra a la carpeta de los manifiestos:

```bash
cd ~/som-api-demo/k8s
```

Trae la versión actual del script desde GitHub:

```bash
git pull
```

Revisa que el script tenga los subcomandos nuevos. `grep -E` muestra solo las líneas que contienen `csv` o `docente`; deben aparecer `claves ARCHIVO.csv`, `tabla ARCHIVO.csv [IP]` y `docente`:

```bash
./gestionar-ambiente.sh | grep -E 'csv|docente'
```

#### Paso 6.4.2 — Configurar el cupo del docente (una sola vez)

El **cupo del docente** es un ambiente propio para validar y mostrar ejemplos. Su contraseña es tu RUT con dígito verificador, sin puntos ni guion, igual que la de los estudiantes. No aparece en la tabla de acceso ni en el archivo de reservas, y el archivo de la sección no puede usar ese número. Tu RUT queda guardado solo en el servidor, en el archivo `docente.env`, que no se sube al repositorio (`k8s/.gitignore`).

Crea el archivo en la carpeta `k8s`:

```bash
vi docente.env
```

Escribe estas dos líneas, con tu RUT **sin** dígito verificador, y guarda con `Esc`, `:wq` y `Enter`:

```text
DOCENTE_N=20
DOCENTE_RUT=<RUT_DOCENTE>
```

> ⚠️ El RUT de abajo es un EJEMPLO — escribe el tuyo (Sección 4).
>
> ❌ Incorrecto: `DOCENTE_RUT=<12345678>` (dejaste los símbolos < >)
> ❌ Incorrecto: `DOCENTE_RUT=123456785` (incluiste el dígito verificador: el script lo calcula)
> ✅ Correcto: `DOCENTE_RUT=12345678`

Deja el archivo legible solo para tu usuario. `600` significa lectura y escritura para el dueño, y nada para los demás:

```bash
chmod 600 docente.env
```

Desde ahora, cada vez que ejecutes `claves` (con o sin archivo de la sección), el cupo 20 recibe tu contraseña. Si el Secret ya existe y no quieres cambiar las contraseñas de los demás (por ejemplo, con la sección en curso), aplica solo la tuya. El script cambia solo la clave `est-20` del Secret y reinicia solo el pod `est-20`; sus volúmenes se conservan:

```bash
./gestionar-ambiente.sh docente
```

Resultado esperado:

```text
Secret editor-claves: cupo 20 con la contrasena del docente.
pod "est-20" deleted
Revise que vuelva a 2/2 Running: kubectl -n cuy6142 get pod est-20
```

Cuando el pod vuelva a `2/2 Running`, entra a `http://<IP_PUBLICA_SERVIDOR>:30120` en una ventana privada, con tu RUT con dígito verificador. Para la shell del mismo pod:

```bash
kubectl -n cuy6142 exec -it est-20 -c editor -- bash
```

`exec -it` abre una terminal interactiva dentro del contenedor `editor`, como el usuario `coder`, con `.venv` activo. Se sale con `exit`.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-12)

#### Paso 6.4.3 — Crear el archivo de la sección

El archivo es un CSV en UTF-8, con una línea de encabezado y una línea por estudiante:

| Columna | Contenido | Ejemplo |
| --- | --- | --- |
| `N` | Número de cupo, de 1 a 19, sin repetir. Es el número del pod (`est-N`). El 20 es el cupo del docente | `1` |
| `rut` | RUT **sin** dígito verificador, 7 u 8 dígitos. Se aceptan puntos, y un guion con dígito se descarta | `16123463` |
| `apellido_paterno` | Apellido paterno | `Perez` |
| `apellido_materno` | Apellido materno. Puede quedar vacío | `Rojas` |
| `nombres` | Nombres | `Juan Andres` |

Ningún campo puede llevar comas, porque la coma separa las columnas.

Crea el archivo con `vi`, con el nombre de la sección:

```bash
vi <ARCHIVO_SECCION>
```

> ⚠️ El nombre de abajo es un EJEMPLO — usa el de tu sección (Sección 4).
>
> ❌ Incorrecto: `vi <seccion-D2.csv>` (dejaste los símbolos < >)
> ❌ Incorrecto: `vi seccion-D2.txt` (el script reconoce el archivo por la extensión `.csv`)
> ✅ Correcto: `vi seccion-D2.csv`

Escribe `i` para insertar, pega el contenido con el botón derecho del mouse en PuTTY y guarda con `Esc`, `:wq` y `Enter`. Ejemplo de contenido (datos ficticios; la segunda línea muestra un apellido materno vacío):

```text
N,rut,apellido_paterno,apellido_materno,nombres
1,16123463,Perez,Rojas,Juan Andres
2,17234567,Soto,,Maria Jose
```

#### Paso 6.4.4 — Generar las contraseñas desde el archivo

Crea el Secret `editor-claves` con el RUT con dígito verificador de cada estudiante y una contraseña al azar para cada cupo sin estudiante. Reemplaza el Secret anterior:

```bash
./gestionar-ambiente.sh claves <ARCHIVO_SECCION>
```

Resultado esperado (con 13 estudiantes y el cupo del docente):

```text
Archivo seccion-D2.csv: 13 estudiantes.
secret/editor-claves configured
Secret editor-claves listo: 13 estudiantes, 6 cupos de reserva y el cupo 20 del docente.
```

Sin `docente.env`, la última línea dice `13 estudiantes y 7 cupos de reserva`: el cupo 20 queda como reserva.

Si el archivo tiene errores, el script muestra una línea `ERROR linea ...` por cada uno y no cambia el Secret: corrige el archivo y repite.

👉 [Pincha acá si algo te falló en este paso (Anexo 1)](#problema-12)

#### Paso 6.4.5 — Dejar los ambientes limpios

Una sección nueva empieza con los ambientes vacíos: aplica el Paso 27 completo (elimina el StatefulSet, elimina los volúmenes y aplica `20-estudiantes.yaml`). Los pods nuevos leen las contraseñas del Paso 6.4.4 al arrancar.

Si la sección ya trabajó en el ambiente y solo cambiaron las contraseñas (por ejemplo, se corrigió un RUT), no borres los volúmenes: reinicia los pods de a uno, y sus archivos y sus órdenes se conservan:

```bash
kubectl -n cuy6142 rollout restart statefulset est
```

Espera a que los 20 pods queden `2/2 Running`:

```bash
watch -n 10 kubectl -n cuy6142 get pods
```

#### Paso 6.4.6 — Generar la tabla de acceso

Genera la tabla con la IP pública actual del servidor:

```bash
./gestionar-ambiente.sh tabla <ARCHIVO_SECCION>
```

Resultado esperado (parte inicial; datos ficticios):

```text
# Tabla de acceso - Actividad 2.4.2 CUY6142

Busque su nombre. La contrasena de su editor es su RUT con digito verificador, sin puntos
ni guion (si termina en K, en mayuscula). Use solo su fila.

| N | Estudiante | TU_URL_EDITOR (navegador) | TU_URL_SOM (solo Postman) | TU_URL_SWAGGER (navegador) |
| --- | --- | --- | --- | --- |
| 01 | Perez Rojas, Juan Andres | http://54.210.10.20:30101 | http://54.210.10.20:30201/api/v2 | http://54.210.10.20:30201/api/v2/docs |
| 02 | Soto, Maria Jose | http://54.210.10.20:30102 | http://54.210.10.20:30202/api/v2 | http://54.210.10.20:30202/api/v2/docs |
```

El script deja dos archivos en la carpeta `k8s`:

| Archivo | Contenido | Destino |
| --- | --- | --- |
| `tabla-acceso-AAAAMMDD-HHMM.md` | Nombre y URL de cada estudiante; los cupos sin estudiante dicen `Reserva`. Sin contraseñas y sin el cupo del docente | Se publica en AVA |
| `reservas-AAAAMMDD-HHMM.md` | Contraseña de cada cupo de reserva | Solo docente. No se publica |

Para llevar la tabla a tu laptop, selecciona el texto en la ventana de PuTTY (se copia solo) y pégalo en Typora. Para ver las contraseñas de reserva cuando las necesites:

```bash
cat reservas-*.md
```

Las contraseñas no dependen de la IP. Si la IP pública cambia (laboratorio reiniciado sin IP elástica), repite solo este paso y publica la tabla nueva. Con una IP elástica asociada al servidor, la IP no cambia y la tabla sirve mientras dure la sección.

#### Paso 6.4.7 — Probar el acceso

1. En una ventana privada del navegador, abre la URL del editor de un cupo de reserva y entra con su contraseña (archivo `reservas-*.md`).
2. Abre la URL del editor de un estudiante y escribe una contraseña equivocada: debe responder **Incorrect password**.
3. Entra a tu cupo (`http://<IP_PUBLICA_SERVIDOR>:30120`) con tu RUT con dígito verificador.

---

## Anexo 1 — Troubleshooting

### Problema 1

**`git pull` responde un conflicto, o `unzip` pregunta `replace editor/Dockerfile? [y]es, [n]o, [A]ll...`**

`unzip` pregunta porque ya existe una versión anterior de los archivos: responde `A` para reemplazarlos todos.

Si `git pull` responde un conflicto, tienes cambios locales sin subir. Revísalos:

```bash
git status
```

### Problema 2

**`docker build` falla en la instalación de Ruff, o muestra `AVISO: no se pudo instalar ms-python.python`**

Las extensiones se descargan desde `open-vsx.org` durante la construcción. Si falla Ruff, la construcción se detiene: revisa que la laptop tenga internet y que la página `https://open-vsx.org` abra en el navegador, y repite el Paso 2.

Si falla solo la extensión Python, la construcción continúa y el editor funciona con Ruff, pero sin autocompletado. Repite el Paso 2: suele ser un corte momentáneo de Open VSX. Si persiste, puedes publicar la imagen igual y avisar a los estudiantes.

### Problema 3

**En la prueba local, el contenedor termina con `ERROR: no existe la contrasena /etc/claves/est-1`**

El wrapper no encontró el archivo de la contraseña, o no lo puede leer. Revisa que exista y sea legible:

```bash
ls -l /tmp/claves-prueba
```

Debe mostrar `est-1` con permisos `-r--r--r--`. Si el sistema usa SELinux (no es el caso de openSUSE con AppArmor), agrega `:z` al final del `-v` del `docker run`.

### Problema 4

**PuTTY responde `Server refused our key`, `No supported authentication methods available` o `Connection timed out`**

- `Server refused our key` o `No supported authentication methods`: el usuario debe ser `ubuntu` (no `ec2-user`) y la llave, `labsuser.ppk` del mismo laboratorio, cargada en **Connection → SSH → Auth → Credentials**.
- `Connection timed out`: la instancia no está **En ejecución**, la IP no es la pública actual, o al grupo de seguridad le falta la regla SSH (Paso 7).

### Problema 5

**`kubectl get nodes` responde `permission denied` sobre `/etc/rancher/k3s/k3s.yaml`, o aparecen pods de `traefik` o `svclb`**

La configuración no estaba en `/etc/rancher/k3s/config.yaml` al instalar k3s (Paso 11). Revisa que exista:

```bash
cat /etc/rancher/k3s/config.yaml
```

Si falta, cópiala (Paso 11) y reinicia k3s para que la lea:

```bash
sudo systemctl restart k3s
```

Mientras tanto, para usar `kubectl` sin `sudo`, deja legible el archivo de acceso al clúster:

```bash
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
```

Si el taint no aparece después del reinicio, aplícalo a mano. `-l` elige el nodo por la etiqueta que k3s pone al servidor:

```bash
kubectl taint nodes -l node-role.kubernetes.io/control-plane=true CriticalAddonsOnly=true:NoExecute
```

### Problema 6

**`kubectl get nodes` no muestra los 5 agentes después de 5 minutos**

Conéctate con PuTTY a un agente que falte (su IP pública en `<IP_PUBLICA_AGENTE>`, usuario `ubuntu`) y revisa el registro de los datos de usuario:

```bash
sudo tail -n 30 /var/log/cloud-init-output.log
```

Revisa el estado del servicio de k3s del agente:

```bash
sudo systemctl status k3s-agent
```

Muestra sus últimos mensajes:

```bash
sudo journalctl -u k3s-agent -n 30 --no-pager
```

Causas frecuentes:

- `connection refused` o `timeout` hacia `:6443`: la IP privada del servidor está mal, o falta la regla de tráfico interno del grupo de seguridad (Paso 7, punto 5).
- `token` inválido o `unauthorized`: el token quedó incompleto.
- `k3s-agent` no existe: la versión estaba mal escrita y el instalador falló (lo indica `cloud-init-output.log`).

Para corregir la URL o el token, edita el archivo donde el instalador los guardó:

```bash
sudo vi /etc/systemd/system/k3s-agent.service.env
```

Y reinicia el agente:

```bash
sudo systemctl restart k3s-agent
```

Si el instalador falló, la vía más rápida es terminar ese agente y lanzar uno nuevo con los datos de usuario corregidos (Paso 15, con **Número de instancias** `1`).

### Problema 7

**Los pods quedan en `Pending` o en `ContainerCreating` por más de 10 minutos**

Muestra los eventos del pod; la causa aparece al final, en **Events**:

```bash
kubectl -n cuy6142 describe pod est-<NUMERO_ESTUDIANTE>
```

| Mensaje en Events | Causa | Solución |
| --- | --- | --- |
| `didn't match pod topology spread constraints` | Faltan agentes `Ready`: la regla de reparto no permite poner más de la cuenta en los demás | Revisa `kubectl get nodes` (Problema 6) |
| `Insufficient memory` | Algún agente es `t3.small` y no `t3.medium` | Revisa el tipo de los agentes en la consola EC2 |
| `secret "editor-claves" not found` | Falta el Paso 19 | Ejecuta `./gestionar-ambiente.sh claves` (o `claves <ARCHIVO_SECCION>`, Paso 6.4.4) |
| `pulling image` por mucho tiempo | La descarga de la imagen del editor todavía no termina | Espera; la primera vez puede tardar varios minutos |
| `ErrImagePull` o `ImagePullBackOff` | La imagen no está publicada o el nombre está mal | Revisa el Paso 4 en Docker Hub |
| `1 node(s) had untolerated taint` | Es informativo: el servidor no recibe estudiantes | Nada, si los demás nodos están disponibles |

### Problema 8

**Un pod queda en `Init:Error`, `Init:CrashLoopBackOff` o `CrashLoopBackOff`**

Muestra el registro del contenedor de inicio, que copia la plantilla:

```bash
kubectl -n cuy6142 logs est-<NUMERO_ESTUDIANTE> -c preparar-home
```

Muestra el registro del editor:

```bash
kubectl -n cuy6142 logs est-<NUMERO_ESTUDIANTE> -c editor
```

- `ERROR: no existe la contrasena /etc/claves/est-N`: el Secret no tiene la clave de ese estudiante. Regenera las contraseñas y reinicia los pods (Sección 6.2, "Cambiar todas las contraseñas").
- `Permission denied` en `/mnt/home`: el volumen no se creó con permisos de escritura. Restablece ese ambiente:

```bash
./gestionar-ambiente.sh restablecer <NUMERO_ESTUDIANTE>
```

### Problema 9

**El navegador no abre el editor, o lo abre pero no acepta la contraseña**

- **La página no carga (tiempo agotado):** falta la regla `30101-30120` en el grupo de seguridad, la IP no es la pública actual, o el navegador cambió la dirección a `https://` (escríbela con `http://`). Revisa también que el pod esté `2/2 Running`.
- **`Incorrect password` con el archivo de la sección:** el estudiante escribió el RUT con puntos, guion, sin dígito verificador o con la `k` en minúscula; o el RUT está mal transcrito en el archivo. Si es el archivo, corrige la fila, repite el Paso 6.4.4 y reinicia solo su pod (sus archivos y su SOM se conservan):

```bash
kubectl -n cuy6142 delete pod est-<NUMERO_ESTUDIANTE>
```

- **`Incorrect password` sin el archivo de la sección:** la tabla es anterior a un `claves --forzar`, o los pods no se reiniciaron después de ese comando. Genera la tabla de nuevo (Paso 23).
- **Pide la contraseña una y otra vez:** hay dos editores abiertos en el mismo navegador; la cookie es por IP, no por puerto (Paso 24). Usa una ventana privada distinta para cada uno.
- **La terminal no muestra `(.venv)`:** cierra la terminal (ícono de papelera) y abre una nueva. Si sigue igual, el pod se creó sin la plantilla: restablécelo.

### Problema 10

**Un pod se reinicia (`RESTARTS` mayor que 0) y `describe` muestra `OOMKilled`, o un agente supera el 85% de memoria**

`OOMKilled` significa que el contenedor superó su límite de memoria y el sistema lo detuvo. Busca en qué contenedor ocurrió:

```bash
kubectl -n cuy6142 describe pod est-<NUMERO_ESTUDIANTE>
```

- **Si es un caso aislado:** el pod se reinicia solo y el estudiante recupera su trabajo (el editor guarda los archivos al segundo de escribir).
- **Si se repite o el agente está sobre 85%:** la medida más efectiva es apagar el servidor de lenguaje Jedi (~85 MiB menos por estudiante, se pierde el autocompletado; Ruff sigue marcando errores). En `editor/plantilla/settings.json` cambia `"python.languageServer": "Jedi"` por `"python.languageServer": "None"`, construye y publica la imagen con una etiqueta nueva (`v2`), cambia `v1` por `v2` en las dos líneas `image:` del editor en `20-estudiantes.yaml`, y aplica el Paso 27 para recrear los ambientes.

La etiqueta tiene que ser nueva: los agentes no vuelven a descargar una imagen con una etiqueta que ya tienen (`imagePullPolicy: IfNotPresent`).

### Problema 11

**Después de reiniciar el laboratorio, los agentes aparecen `NotReady` o los pods en `Unknown`**

Las instancias tardan uno o dos minutos en arrancar k3s. Espera y repite `./gestionar-ambiente.sh estado`. Si un agente sigue `NotReady`, revisa en la consola EC2 que esté **En ejecución** e inícialo si quedó detenido.

### Problema 12

**`claves <ARCHIVO_SECCION>`, `tabla <ARCHIVO_SECCION>` o `docente` responde `ERROR`**

El script revisa el archivo completo antes de cambiar algo, y muestra una línea por cada error:

| Mensaje | Causa | Solución |
| --- | --- | --- |
| `ERROR: no se puede leer el archivo ...` | El nombre está mal escrito o el archivo está en otra carpeta | Revisa con `ls *.csv` desde `~/som-api-demo/k8s` |
| `ERROR linea L: N debe ser un numero entre 1 y 20` | La columna `N` está vacía, no es un número o es mayor que 20 | Corrige la línea `L` |
| `ERROR linea L: el RUT debe tener 7 u 8 digitos, sin digito verificador` | El RUT tiene letras, espacios internos o un largo distinto | Escribe solo los dígitos del RUT, sin el dígito verificador |
| `ERROR linea L: el numero N esta repetido` | Dos estudiantes tienen el mismo cupo | Asigna otro número a uno de ellos |
| `ERROR: el numero 20 es el cupo del docente (docente.env)` | El archivo de la sección asigna el cupo 20 a un estudiante | Dale un número libre entre 1 y 19 |
| `ERROR en .../docente.env: DOCENTE_N ...` o `DOCENTE_RUT ...` | `docente.env` tiene un número fuera de rango, o el RUT con letras o un largo distinto. Mientras tenga el error, ningún subcomando funciona | Corrige el archivo (Paso 6.4.2) |
| `ERROR: no existe .../docente.env` (en `docente`) | Falta el Paso 6.4.2 | Crea el archivo |
| `ERROR: el Secret editor-claves ...` o `secrets "editor-claves" not found` (en `tabla`) | Falta el Paso 6.4.4 | Ejecuta `./gestionar-ambiente.sh claves <ARCHIVO_SECCION>` |

Si un nombre aparece incompleto o mezclado con otra columna en la tabla, esa línea del archivo tiene una coma de más: quítala y repite los Pasos 6.4.4 y 6.4.6.

---

## Anexo 2 — Arquitectura y Notas Conceptuales

### A. Arquitectura

```text
PC del estudiante                      Instancias EC2 (grupo de seguridad k3s-cuy6142)
-----------------                      ------------------------------------------------
Navegador --- http :301NN --+
                            +------>   k3s-servidor (t3.small)   IP publica = la de la tabla
Postman ----- http :302NN --+            plano de control: API (6443), programador, SQLite
                                         kube-proxy: recibe el NodePort y lo reenvia
                                              |
                                              | red de pods (flannel VXLAN, IP privadas)
                                              v
                                       k3s-agente x5 (t3.medium), 4 pods cada uno
                                         pod est-N
                                           +-- init preparar-home (copia la plantilla, 1a vez)
                                           +-- editor  code-server :8080 --+
                                           |                               | localhost:8081
                                           +-- som     SOM v2.1    :8081 <-+
                                           +-- volumen home-est-N       -> /home/coder
                                           +-- volumen datos-som-est-N  -> /app/data
                                           +-- Secret editor-claves     -> /etc/claves

Editor (Git) --- https :443 --->  GitHub
```

### B. Cómo llega una solicitud del estudiante a su pod

1. El navegador del estudiante 07 se conecta a `http://<IP_PUBLICA_SERVIDOR>:30107`.
2. El grupo de seguridad deja pasar el puerto `30107` (regla `30101-30120`).
3. En el servidor, **kube-proxy** tiene una regla para cada NodePort: el `30107` pertenece al Service `est-7`, que selecciona al pod `est-7` por su etiqueta `statefulset.kubernetes.io/pod-name`.
4. kube-proxy reenvía la conexión a la IP del pod `est-7`, que está en algún agente, por la red de pods (flannel).
5. El contenedor `editor` responde en el puerto `8080`.

Un NodePort escucha en **todos** los nodos. Los estudiantes usan siempre la IP del servidor, aunque su pod esté en otro nodo: así reciben una sola IP en la tabla.

### C. Decisiones de diseño

- **Un pod por estudiante, con su propio SOM.** Aísla los datos: cada estudiante usa los `com_id` `0000005` a `0000007` y obtiene la suscripción `20000001`, como dice la actividad. Una falla afecta a un solo estudiante.
- **Editor y SOM en el mismo pod.** Comparten la red del pod, por eso el editor llega a SOM en `http://localhost:8081` y los programas de la actividad no cambian.
- **StatefulSet.** Da nombres estables (`est-1`... `est-20`) y crea los volúmenes de cada pod a partir de una plantilla (`volumeClaimTemplates`). Un Deployment no tiene ninguna de las dos cosas.
- **Servidor solo para el plano de control.** Con el taint `CriticalAddonsOnly`, el servidor solo ejecuta los componentes del sistema. Si un estudiante consume mucha memoria, el que sufre es un agente, no la API del clúster.
- **Reparto con `topologySpreadConstraints`.** Obliga a repartir los pods en partes iguales entre agentes (diferencia máxima de 1). Con 5 agentes y 20 pods quedan 4 en cada uno.
- **Volúmenes `local-path`.** Guardan los datos en el disco del agente (`/var/lib/rancher/k3s/storage`). Son simples y rápidos, pero dejan cada pod atado al agente donde se creó su volumen: si ese agente se cae, sus 4 estudiantes esperan a que vuelva, o se les entrega un cupo de reserva.
- **Memoria medida, no estimada.** El 08/10/2026 se midió el editor con navegador conectado, un archivo Python abierto y la terminal: ~560 MiB con Jedi, ~475 MiB sin Jedi y ~375 MiB solo con Ruff. SOM usa ~34 MiB. Con eso, un `t3.small` (~1,3 GB libres para pods) admite 2 estudiantes y un `t3.medium` (~3,2 GB) admite 4 con margen.
- **Funciones de IA del editor desactivadas** (`chat.disableAIFeatures`): no aportan a la actividad y su proceso consume ~70 MiB por estudiante.

---

## Anexo 3 — Desglose de Comandos

### A. Docker (Parte A)

```bash
docker build -f editor/Dockerfile -t moscosov/cuy6142-editor:v1 .
```

Construye una imagen. `-f` indica el `Dockerfile`; `-t` le da nombre (`moscosov/cuy6142-editor`) y etiqueta (`v1`); el `.` final es el **contexto de construcción**: la carpeta cuyos archivos puede copiar el `Dockerfile`.

```bash
docker run --rm -p 8080:8080 -e POD_NAME=est-1 -v /tmp/claves-prueba:/etc/claves:ro moscosov/cuy6142-editor:v1
```

Crea y ejecuta un contenedor. `--rm` lo borra al detenerse; `-p 8080:8080` publica el puerto (laptop:contenedor); `-e` define una variable de entorno; `-v` monta una carpeta de la laptop dentro del contenedor (`:ro`, solo lectura).

```bash
docker login
```

Inicia sesión en Docker Hub para poder publicar imágenes.

```bash
docker push moscosov/cuy6142-editor:v1
```

Sube la imagen a Docker Hub.

### B. Git y archivos (Partes A y C)

```bash
git switch desarrollo
```

Cambia a la rama `desarrollo`.

```bash
unzip <RUTA_DEL_ZIP> -d .
```

Descomprime un archivo ZIP; `-d` indica la carpeta de destino.

```bash
chmod +x k8s/gestionar-ambiente.sh
```

Agrega el permiso de ejecución (`+x`), para poder ejecutar el script con `./`.

```bash
git clone -b desarrollo https://github.com/moscosov/som-api-demo.git
```

Descarga una copia del repositorio; `-b` elige la rama.

### C. Instalación de k3s (Partes C y D)

```bash
curl -sfL https://get.k3s.io | sh -
```

Descarga el instalador oficial de k3s y lo ejecuta. `-s` sin barra de progreso, `-f` falla ante un error HTTP, `-L` sigue redirecciones. El instalador usa `sudo` cuando lo necesita. En el servidor lee `/etc/rancher/k3s/config.yaml`; en los agentes, las variables `K3S_URL`, `K3S_TOKEN` e `INSTALL_K3S_VERSION` lo convierten en agente.

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

Muestra el token del clúster. Requiere `sudo` porque el archivo es solo de root.

```bash
hostname -I
```

Lista las IP de la instancia; la primera es la privada.

```bash
sudo systemctl restart k3s
```

Reinicia el servicio de k3s del servidor (`k3s-agent` en los agentes).

```bash
sudo journalctl -u k3s-agent -n 30 --no-pager
```

Muestra los últimos 30 mensajes del servicio `k3s-agent`; `--no-pager` los imprime sin paginar.

### D. kubectl (Partes C a G y Sección 6)

`kubectl` es el cliente de la API de Kubernetes. `-n cuy6142` indica el espacio de nombres; sin él, `kubectl` usa `default`.

```bash
kubectl get nodes
```

Lista los nodos del clúster con su estado (`Ready`), rol y versión.

```bash
kubectl apply -f 20-estudiantes.yaml
```

Crea o actualiza los objetos definidos en un archivo. Si ya existen, aplica solo las diferencias.

```bash
kubectl -n cuy6142 get pods -o wide
```

Lista los pods; `-o wide` agrega la IP y el **nodo** de cada uno.

```bash
watch -n 10 kubectl -n cuy6142 get pods -o wide
```

`watch` repite un comando cada 10 segundos (`-n 10`) y muestra el resultado actualizado. Se sale con `Ctrl+C`.

```bash
kubectl -n cuy6142 describe pod est-7
```

Muestra el detalle de un pod; al final, la sección **Events** explica por qué no arranca.

```bash
kubectl -n cuy6142 logs est-7 -c som --tail 20
```

Muestra el registro de un contenedor del pod; `-c` elige el contenedor (`editor`, `som` o `preparar-home`) y `--tail 20` las últimas 20 líneas.

```bash
kubectl -n cuy6142 delete pod est-7
```

Elimina un pod. El StatefulSet crea uno nuevo con el mismo nombre y los mismos volúmenes.

```bash
kubectl -n cuy6142 delete pvc -l app.kubernetes.io/name=est
```

Elimina los **PersistentVolumeClaim** (volúmenes) que tienen esa etiqueta (`-l`). Con `local-path`, sus datos se borran del disco del agente.

```bash
kubectl -n cuy6142 rollout restart statefulset est
```

Reinicia los pods del StatefulSet de a uno, sin perder sus volúmenes.

```bash
kubectl top nodes
```

Muestra el uso actual de CPU y memoria de cada nodo (lo entrega `metrics-server`).

```bash
kubectl -n cuy6142 top pods --containers
```

Muestra el uso de cada contenedor de cada pod.

### E. Script `gestionar-ambiente.sh`

| Subcomando | Qué hace |
| --- | --- |
| `claves` | Crea el Secret `editor-claves` con una contraseña al azar de 8 caracteres por estudiante (letras y números sin `0`, `o`, `1`, `l`, `i`). Si ya existe, no lo cambia |
| `claves --forzar` | Genera contraseñas nuevas para todos. Luego hay que reiniciar los pods |
| `claves <ARCHIVO_SECCION>` | Valida el archivo de la sección y crea el Secret con el RUT con dígito verificador (módulo 11) de cada estudiante, sin puntos ni guion y con la K en mayúscula. Los cupos sin estudiante reciben una contraseña al azar. Siempre reemplaza el Secret |
| `servicios` | Escribe `servicios-generados.yaml` con los 20 Services NodePort y lo aplica |
| `tabla` | Obtiene la IP pública del servidor (IMDSv2), lee las contraseñas del Secret y escribe `credenciales-AAAAMMDD-HHMM.md`, con las URL completas del editor, de SOM (para Postman) y de Swagger de cada estudiante |
| `tabla <IP_PUBLICA_SERVIDOR>` | Igual, con la IP que se indica (cuando el script no logra obtenerla solo) |
| `tabla <ARCHIVO_SECCION> [IP]` | Escribe `tabla-acceso-AAAAMMDD-HHMM.md` (nombre y URL de cada estudiante, sin contraseñas, para publicar en AVA) y `reservas-AAAAMMDD-HHMM.md` (contraseñas de los cupos de reserva, solo docente). Reconoce el archivo por la extensión `.csv` |
| `docente` | Lee `docente.env`, cambia en el Secret solo la clave del cupo del docente (RUT con dígito verificador) y reinicia solo ese pod. Con `docente.env`, todos los modos de `claves` aplican esa contraseña al cupo, y `tabla` lo omite (la tabla sin archivo muestra `(docente)` en lugar de la contraseña) |
| `estado` | Muestra nodos, pods (con nodo y reinicios) y memoria por nodo |
| `restablecer N` | Pide confirmación, borra los volúmenes del estudiante N y crea un pod nuevo desde la plantilla |
| `prueba-carga` | Ejecuta `carga_masiva.py` en los 20 pods a la vez (con `kubectl exec`) y resume el resultado de cada uno |

---

## Anexo 4 — Explicación de Configuración

### A. `k8s/k3s/servidor-config.yaml` (Paso 11)

| Línea | Significado |
| --- | --- |
| `write-kubeconfig-mode: "0644"` | Deja legible `/etc/rancher/k3s/k3s.yaml`, el archivo de acceso al clúster, para usar `kubectl` sin `sudo` |
| `disable: traefik, servicelb` | No instala el Ingress Traefik ni el balanceador ServiceLB: este ambiente usa NodePort, y así se ahorra memoria |
| `node-taint: CriticalAddonsOnly=true:NoExecute` | Restricción del servidor: solo admite pods que la toleran (los del sistema). Los pods de estudiantes no la toleran |

### B. `k8s/k3s/agente-user-data.sh` (Paso 14)

| Línea | Significado |
| --- | --- |
| `#!/bin/bash` | Indica que el script se ejecuta con bash. EC2 lo ejecuta como root en el primer arranque |
| `K3S_URL` | Dirección de la API del servidor. Su presencia hace que el instalador configure un agente |
| `K3S_TOKEN` | Contraseña del clúster |
| `INSTALL_K3S_VERSION` | Versión exacta, igual a la del servidor |
| `curl ... \| sh -` | Descarga y ejecuta el instalador |

### C. `editor/Dockerfile` (Paso 2)

| Instrucción | Significado |
| --- | --- |
| `ARG CODE_SERVER_VERSION=4.141.0-debian` y `FROM codercom/code-server:...` | Parte de la imagen oficial de `code-server`, en una versión fija (Debian 13) |
| `ARG RUFF_EXT` / `ARG PYTHON_EXT` | Versiones fijas de las extensiones |
| `USER root` y `apt-get install python3 python3-venv` | Instala Python y el módulo para entornos virtuales |
| `rm -f /etc/sudoers.d/nopasswd` | Quita al usuario `coder` el `sudo` sin contraseña: el estudiante no lo necesita |
| `mkdir -p /opt/extensiones` | Carpeta de extensiones fuera de `/home/coder`, para que no se copie a cada volumen (83 MB menos por estudiante) |
| `COPY ... iniciar-editor.sh preparar-home.sh` | Copia el wrapper y el script del contenedor de inicio |
| `USER coder` y `code-server --install-extension` | Instala Ruff y Python desde Open VSX en `/opt/extensiones` |
| `--list-extensions --show-versions` | Deja en el registro de construcción la lista de extensiones instaladas |
| `COPY scripts/...` | Copia los tres programas a la plantilla `/home/coder/Formativa242` |
| `python3 -m venv` y `pip install requests` | Crea `.venv` en la misma ruta absoluta que tendrá en el pod (un entorno virtual no funciona si cambia de ruta) |
| `COPY ... settings.json`, `gitconfig`, `bashrc-cuy6142` | Configuración del editor, de Git y de la terminal |
| `rm -rf /home/coder/.config/code-server` | Borra la configuración que `code-server` creó al instalar extensiones (trae una contraseña al azar que no se usa) |
| `ENTRYPOINT ["/usr/local/bin/iniciar-editor.sh"]` | El contenedor arranca con el wrapper |

### D. `editor/iniciar-editor.sh` (wrapper)

Un **wrapper** es un script pequeño que prepara algo y luego lanza el programa real en su lugar.

| Parte | Significado |
| --- | --- |
| `NOMBRE_POD="${POD_NAME:-$(hostname)}"` | Nombre del pod (`est-7`), que entrega Kubernetes en `POD_NAME`; si no está, usa el nombre del equipo |
| `ARCHIVO_CLAVE="/etc/claves/${NOMBRE_POD}"` | Cada estudiante lee el archivo con el nombre de su pod |
| `if [ ! -r ... ]` | Si el archivo no existe o no se puede leer, termina con un mensaje claro |
| `export PASSWORD=...` | `code-server` toma la contraseña de la variable `PASSWORD` |
| `exec dumb-init /usr/bin/code-server` | `exec` reemplaza el wrapper por `code-server`; `dumb-init` queda como proceso principal (reenvía señales y recoge procesos huérfanos) |
| `--bind-addr 0.0.0.0:8080` | Escucha en todas las interfaces del pod, puerto 8080 |
| `--auth password` | Pide contraseña |
| `--extensions-dir /opt/extensiones` | Usa las extensiones de la imagen |
| `--disable-telemetry --disable-update-check` | Sin envío de datos ni avisos de actualización |
| `--disable-workspace-trust` | No pregunta si se confía en la carpeta |
| `/home/coder/Formativa242` | Carpeta que se abre al entrar |

### E. `editor/preparar-home.sh` (contenedor de inicio)

| Parte | Significado |
| --- | --- |
| `MARCA=/mnt/home/.plantilla-cuy6142` | Archivo que indica que la plantilla ya se copió |
| `if [ -f "$MARCA" ]; then exit 0` | Si ya se copió, no hace nada: un reinicio del pod no borra el trabajo del estudiante |
| `find ... -exec cp -a {} /mnt/home/ \;` | Copia cada elemento de la plantilla (incluidos los ocultos), conservando permisos y fechas. Copia el contenido y no la carpeta misma, porque la carpeta del volumen pertenece a root |

### F. Plantilla de la carpeta personal

**`settings.json`** (configuración del editor):

| Opción | Efecto |
| --- | --- |
| `editor.tabSize: 4`, `editor.insertSpaces: true`, `editor.detectIndentation: false` | `Tab` inserta siempre 4 espacios, aunque un archivo copiado traiga otra sangría |
| `editor.renderWhitespace: boundary` | Muestra como puntos tenues los espacios al inicio de cada línea: el estudiante "ve" la sangría |
| `editor.guides.indentation`, `highlightActiveIndentation` | Líneas verticales por nivel de sangría, resaltando el bloque actual |
| `editor.bracketPairColorization`, `editor.guides.bracketPairs` | Colorea los pares de paréntesis y llaves |
| `editor.fontSize: 16`, `terminal.integrated.fontSize: 15` | Letra más grande, para leer bien en el laboratorio |
| `files.autoSave: afterDelay` (1 segundo) | Guarda solo: si el pod se reinicia, no se pierde lo escrito |
| `files.trimTrailingWhitespace: true` | Quita los espacios sobrantes al final de las líneas |
| `editor.formatOnSave: false` | No reformatea el código al guardar: las líneas quedan como las indica la actividad |
| `chat.disableAIFeatures: true` | Desactiva las funciones de IA del editor (~70 MiB menos por estudiante) |
| `telemetry.telemetryLevel: off`, `update.mode: none`, `extensions.autoUpdate: false` | Sin telemetría ni actualizaciones durante la clase |
| `security.workspace.trust.enabled: false`, `workbench.startupEditor: none` | Sin preguntas ni pantalla de bienvenida al entrar |
| `git.terminalAuthentication: false` | Git pide usuario y token en la terminal, no en ventanas del editor (igual que el Paso 23-A de la guía anterior) |
| `python.defaultInterpreterPath` | La extensión Python usa el Python de `.venv` |
| `python.languageServer: Jedi` | Autocompletado y ayuda con Jedi (Pylance no está en Open VSX). `None` lo desactiva (Problema 10) |
| `python.terminal.activateEnvironment: false` | La extensión no activa el entorno en la terminal: ya lo hace `.bashrc`, y así no aparecen comandos extra |

**`gitconfig`**: `credential.helper store` (Git guarda el token de GitHub después del primer `push`), `pull.rebase false` (`git pull` junta con merge) e `init.defaultBranch main`. El estudiante agrega su nombre y correo con `git config --global`.

**`bashrc-cuy6142`** (se agrega al final de `.bashrc`): activa `.venv` en cada terminal nueva y, si la terminal se abre en la carpeta personal, entra a `Formativa242`.

### G. `k8s/20-estudiantes.yaml`

| Campo | Significado |
| --- | --- |
| Service `est` con `clusterIP: None` | Service **headless**: no balancea; el StatefulSet lo exige para dar un nombre DNS a cada pod |
| `replicas: 20` | 20 cupos |
| `ordinals.start: 1` | Los pods se numeran desde 1 (`est-1`), igual que la tabla |
| `podManagementPolicy: Parallel` | Crea los 20 pods a la vez |
| `securityContext: runAsUser/runAsGroup/fsGroup 1000` | Todos los procesos corren como el usuario 1000; `fsGroup` deja los archivos del Secret con grupo 1000 |
| `automountServiceAccountToken: false` | El pod no recibe credenciales para la API de Kubernetes: el estudiante no puede ver ni tocar el clúster |
| `enableServiceLinks: false` | No inyecta variables de entorno por cada uno de los 21 Services |
| `topologySpreadConstraints` (`maxSkew: 1`, `DoNotSchedule`, `nodeTaintsPolicy: Honor`) | Reparto en partes iguales entre agentes; el servidor no cuenta porque tiene taint |
| `initContainers: preparar-home` | Contenedor de inicio: monta el volumen `home` en `/mnt/home` y copia la plantilla |
| `env: POD_NAME` desde `fieldRef: metadata.name` | **Downward API**: entrega al contenedor el nombre de su propio pod |
| Volumen `claves` (Secret, `defaultMode: 0440`) | Contraseñas como archivos de solo lectura para el grupo 1000 |
| `resources.requests` | Memoria y CPU reservadas: el programador solo pone un pod donde caben. Editor 600 MiB (medido: ~560), SOM 64 MiB |
| `resources.limits.memory` | Máximo: el editor que supere 1 GiB, o el SOM que supere 160 MiB, se reinicia (`OOMKilled`) en vez de afectar al nodo |
| `readinessProbe` | Kubernetes envía tráfico al pod solo cuando responde: `/healthz` en el editor y `/api/v2/openapi.json` en SOM |
| `livenessProbe` | Si deja de responder por un tiempo (3 minutos en el editor, 2 en SOM), Kubernetes reinicia el contenedor |
| `allowPrivilegeEscalation: false` | Ningún proceso puede obtener más privilegios de los que tiene |
| `volumeClaimTemplates`: `home` (2 GiB) y `datos-som` (256 MiB), clase `local-path` | Un par de volúmenes por pod: `home-est-N` y `datos-som-est-N`. `local-path` no limita el tamaño real; los valores son referenciales |

### H. Services generados por `gestionar-ambiente.sh servicios`

| Campo | Significado |
| --- | --- |
| `name: est-N` | Un Service por estudiante |
| `type: NodePort` | Publica puertos en todos los nodos, dentro del rango 30000-32767 |
| `selector: statefulset.kubernetes.io/pod-name: est-N` | Etiqueta que el StatefulSet pone a cada pod con su nombre: el Service apunta a un solo pod |
| Puerto `editor`: `port 8080`, `nodePort 30100+N` | Editor del estudiante N (por ejemplo, `30107` para el 7) |
| Puerto `som`: `port 8081`, `nodePort 30200+N` | SOM del estudiante N (por ejemplo, `30207` para el 7) |

---

## Anexo 5 — Glosario de Términos Técnicos

**k3s**
Distribución liviana y certificada de Kubernetes, de un solo binario. Incluye containerd, la red flannel, CoreDNS, metrics-server y el aprovisionador de volúmenes `local-path`.

**Nodo servidor y nodo agente**
El servidor ejecuta el plano de control (API, programador, base de datos del clúster). Los agentes ejecutan los pods.

**Taint y toleration**
Un taint es una restricción en un nodo que rechaza los pods que no la toleran. Una toleration es la declaración, en un pod, de que acepta esa restricción.

**Pod y contenedor de inicio (init container)**
Un pod es la unidad mínima de Kubernetes: uno o más contenedores que comparten red y volúmenes. Un contenedor de inicio corre una vez, hasta terminar, antes de los contenedores principales.

**StatefulSet**
Controlador que mantiene un número de pods con nombres estables y volúmenes propios para cada uno.

**Service NodePort y Service headless**
Un NodePort publica un puerto en todos los nodos y lo reenvía a los pods que selecciona. Un headless (`clusterIP: None`) no reenvía tráfico: solo crea nombres DNS para los pods.

**kube-proxy y flannel**
kube-proxy programa en cada nodo las reglas que llevan el tráfico de un Service a sus pods. flannel crea la red entre pods de distintos nodos (VXLAN sobre las IP privadas).

**PersistentVolumeClaim (PVC) y local-path**
Un PVC es la solicitud de un volumen persistente. `local-path` lo cumple con una carpeta en el disco del nodo donde corre el pod.

**Secret**
Objeto de Kubernetes que guarda datos sensibles y los entrega a los pods como archivos o variables.

**Downward API**
Mecanismo que entrega a un contenedor datos de su propio pod, como el nombre.

**Sondas (readiness y liveness)**
Pruebas periódicas que hace el kubelet: readiness decide si el pod recibe tráfico; liveness, si hay que reiniciar el contenedor.

**Requests, limits y OOMKilled**
Requests es lo que un contenedor reserva; limits, lo máximo que puede usar. Un contenedor que supera su límite de memoria es detenido por el sistema (OOMKilled) y Kubernetes lo reinicia.

**code-server y Open VSX**
code-server es VS Code ejecutándose en un servidor y usándose desde el navegador. Open VSX es el repositorio abierto de extensiones que usa code-server en lugar del Marketplace de Microsoft.

**Servidor de lenguaje (Jedi) y Ruff**
Un servidor de lenguaje es un proceso que analiza el código para ofrecer autocompletado y ayuda; Jedi es el que usa la extensión Python cuando no hay Pylance. Ruff es un analizador de código Python, compilado y liviano, que marca errores mientras se escribe.

**Wrapper y dumb-init**
Un wrapper es un script que prepara el entorno y luego lanza el programa real en su lugar. dumb-init es un proceso inicial mínimo que reenvía las señales y recoge procesos huérfanos dentro de un contenedor.

**Datos de usuario (user data) e IMDSv2**
Los datos de usuario son un script que EC2 ejecuta en el primer arranque de una instancia. IMDSv2 es el servicio de metadatos de EC2 (dirección `169.254.169.254`), que entrega datos de la propia instancia, como su IP pública, después de pedir un token.
