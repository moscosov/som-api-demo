#!/bin/sh
# Contenedor de inicio (init container) de cada estudiante.
#
# Copia la plantilla de la carpeta personal (/home/coder de la imagen) al volumen del
# estudiante, montado en /mnt/home. Solo la primera vez: deja un archivo marca y, si la
# marca ya existe, no copia nada. Asi un reinicio del pod no borra el trabajo del estudiante.
set -eu

DESTINO=/mnt/home
MARCA="${DESTINO}/.plantilla-cuy6142"

if [ -f "$MARCA" ]; then
    echo "La carpeta personal ya estaba preparada ($(cat "$MARCA")): no se copia nada."
    exit 0
fi

# Se copia cada elemento de la plantilla (incluidos los ocultos) y no la carpeta misma:
# la carpeta del volumen la crea el aprovisionador como root y no se pueden cambiar sus atributos.
find /home/coder -mindepth 1 -maxdepth 1 -exec cp -a {} "${DESTINO}/" \;
date '+%Y-%m-%d %H:%M:%S' > "$MARCA"
echo "Plantilla copiada al volumen del estudiante."
