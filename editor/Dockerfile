# Imagen del editor web de la Actividad 2.4.2 de CUY6142 (Duoc UC).
#
# Cada estudiante recibe un pod con este editor (code-server: VS Code en el navegador)
# y su propio SOM. La imagen trae todo listo: Python con requests, los tres programas
# de la actividad, Git preconfigurado y las extensiones Ruff y Python.
#
# Se construye desde la RAIZ del repositorio som-api-demo, porque copia la carpeta scripts/:
#   docker build -f editor/Dockerfile -t moscosov/cuy6142-editor:v1 .

# Version fija de code-server (no latest): un cambio de version se decide y se prueba.
ARG CODE_SERVER_VERSION=4.141.0-debian
FROM codercom/code-server:${CODE_SERVER_VERSION}

# Versiones fijas de las extensiones, descargadas desde Open VSX durante la construccion.
ARG RUFF_EXT=charliermarsh.ruff@2026.84.0
ARG PYTHON_EXT=ms-python.python@2026.4.0

# --- 1. Paquetes del sistema (como root) -------------------------------------------------
USER root

# python3 y python3-venv: para crear el entorno virtual de la carpeta Formativa242.
# Se elimina el permiso de sudo sin contrasena del usuario coder: el estudiante no lo necesita.
# /opt/extensiones: carpeta de extensiones fuera de /home/coder, para que no se copie a cada volumen.
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/sudoers.d/nopasswd \
 && mkdir -p /opt/extensiones \
 && chown coder:coder /opt/extensiones

# Wrapper de arranque del editor y script del contenedor de inicio.
COPY editor/iniciar-editor.sh editor/preparar-home.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/iniciar-editor.sh /usr/local/bin/preparar-home.sh

# --- 2. Extensiones (como coder) ----------------------------------------------------------
USER coder

# Ruff: subraya en rojo los errores de sintaxis e indentacion mientras se escribe.
RUN code-server --extensions-dir /opt/extensiones --install-extension "${RUFF_EXT}"

# Python (Microsoft): autocompletado y ayuda con el servidor de lenguaje Jedi.
# Si su instalacion falla, la construccion sigue: el editor funciona igual con Ruff.
RUN code-server --extensions-dir /opt/extensiones --install-extension "${PYTHON_EXT}" \
 || echo "AVISO: no se pudo instalar ${PYTHON_EXT}; revise la lista de extensiones de abajo"

# Muestra en el registro de construccion las extensiones instaladas, con su version.
RUN code-server --extensions-dir /opt/extensiones --list-extensions --show-versions

# --- 3. Plantilla de la carpeta personal /home/coder ---------------------------------------
# El contenedor de inicio copia esta carpeta al volumen de cada estudiante la primera vez.
RUN mkdir -p /home/coder/Formativa242 /home/coder/.local/share/code-server/User

# Los tres programas de la actividad, tal como estan en el repositorio del curso.
COPY --chown=coder:coder scripts/som_relocation.py scripts/carga_masiva.py \
     scripts/listar_ordenes.py /home/coder/Formativa242/

# Entorno virtual con requests, en la misma ruta en que se usara dentro del pod.
RUN python3 -m venv /home/coder/Formativa242/.venv \
 && /home/coder/Formativa242/.venv/bin/pip install --no-cache-dir requests

# Configuracion del editor, de Git y de la terminal.
COPY --chown=coder:coder editor/plantilla/settings.json /home/coder/.local/share/code-server/User/settings.json
COPY --chown=coder:coder editor/plantilla/gitconfig /home/coder/.gitconfig
COPY --chown=coder:coder editor/plantilla/bashrc-cuy6142 /tmp/bashrc-cuy6142
# Se borra la configuracion que code-server creo al instalar las extensiones (trae una contrasena
# al azar que no se usa: la contrasena real llega por la variable PASSWORD).
RUN cat /tmp/bashrc-cuy6142 >> /home/coder/.bashrc \
 && rm /tmp/bashrc-cuy6142 \
 && rm -rf /home/coder/.config/code-server

WORKDIR /home/coder/Formativa242

# El wrapper lee la contrasena del estudiante y lanza code-server.
ENTRYPOINT ["/usr/local/bin/iniciar-editor.sh"]
