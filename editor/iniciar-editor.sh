#!/bin/sh
# Wrapper de arranque del editor (code-server) de cada estudiante.
#
# 1. Lee la contrasena del estudiante desde el Secret editor-claves, montado como archivos
#    en /etc/claves: un archivo por estudiante, con el nombre de su pod (est-1, est-2...).
# 2. La deja en la variable de entorno PASSWORD, que code-server usa para la pantalla de inicio.
# 3. Lanza code-server en el puerto 8080, abriendo la carpeta Formativa242.
#
# POD_NAME lo entrega Kubernetes (Downward API, ver 20-estudiantes.yaml).
set -eu

NOMBRE_POD="${POD_NAME:-$(hostname)}"
ARCHIVO_CLAVE="/etc/claves/${NOMBRE_POD}"

if [ ! -r "$ARCHIVO_CLAVE" ]; then
    echo "ERROR: no existe la contrasena ${ARCHIVO_CLAVE}." >&2
    echo "Revise que el Secret editor-claves tenga la clave ${NOMBRE_POD}." >&2
    exit 1
fi

PASSWORD="$(cat "$ARCHIVO_CLAVE")"
export PASSWORD
echo "Editor de ${NOMBRE_POD}: contrasena cargada desde ${ARCHIVO_CLAVE}."

# dumb-init queda como proceso principal (PID 1): reenvia las senales y recoge procesos huerfanos.
exec dumb-init /usr/bin/code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth password \
    --extensions-dir /opt/extensiones \
    --disable-telemetry \
    --disable-update-check \
    --disable-workspace-trust \
    /home/coder/Formativa242
