#!/bin/bash
# preparar_ambiente_ep2.sh
# AAY1110 Sistemas Operativos Corporativos en Cloud - Evaluacion Parcial N 2
#
# Prepara la instancia B (produccion) con el ambiente de NuevaNet:
#   - Datos de la empresa en /srv/nuevanet/datos
#   - Logs de la aplicacion con distintas antiguedades en /var/log/nuevanet
#   - Respaldos antiguos simulados en /backups
#
# Uso:
#   sudo bash preparar_ambiente_ep2.sh             Prepara (o reinicia) el ambiente
#   sudo bash preparar_ambiente_ep2.sh actividad   Simula un dia de trabajo (opcional)
#   bash preparar_ambiente_ep2.sh ayuda            Muestra esta ayuda
#
# El script nunca elimina respaldos reales: solo reemplaza los respaldos
# simulados que el mismo creo, registrados en su archivo de control.

set -uo pipefail

# --- Configuracion ---
# RAIZ permite probar el script en un directorio aislado (uso docente).
RAIZ="${RAIZ:-}"
DATOS="$RAIZ/srv/nuevanet/datos"
LOGS="$RAIZ/var/log/nuevanet"
DESTINO="$RAIZ/backups"
CONTROL_DIR="$RAIZ/var/lib/nuevanet-ep2"
CONTROL="$CONTROL_DIR/simulados.lst"

# Antiguedad (dias) y tamano aproximado (MB) de cada log de prueba
EDADES_LOG=(1 2 4 10 27 30 45)
TAMANOS_LOG=(2 2 5 10 20 30 40)

# Antiguedad (dias) y tipo de cada respaldo simulado
EDADES_RESP=(10 27 30 40)
TIPOS_RESP=(completo completo diferencial completo)

AHORA=$(date +%s)

# --- Funciones de apoyo ---
mensaje() {
    echo "[preparador] $1"
}

error() {
    echo "[preparador] ERROR: $1" >&2
    exit 1
}

ayuda() {
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
}

# Fecha de modificacion y nombre se calculan desde la antiguedad en dias
epoch_de() {
    echo $(( AHORA - $1 * 86400 ))
}

validar() {
    if [ -z "$RAIZ" ] && [ "$(id -u)" -ne 0 ]; then
        error "debe ejecutarse con sudo: sudo bash $0"
    fi
    for cmd in tar gzip sha256sum awk touch; do
        command -v "$cmd" > /dev/null 2>&1 || error "falta el comando $cmd"
    done
}

# --- Datos de NuevaNet ---
crear_datos() {
    mensaje "Creando datos de NuevaNet en $DATOS"
    rm -rf "$DATOS"
    mkdir -p "$DATOS/contratos" "$DATOS/config"

    awk 'BEGIN {
        srand(1110);
        split("Santiago,Melipilla,Valparaiso,Talagante,Rancagua,San Antonio", c, ",");
        split("INTERNET,TELEFONIA,TV,EMPRESAS", s, ",");
        print "cliente_id,razon_social,comuna,servicio,fecha_alta";
        for (i = 1; i <= 120; i++)
            printf "CL-%05d,Cliente %03d SpA,%s,%s,2025-%02d-%02d\n", 10000 + i, i, c[int(rand()*6)+1], s[int(rand()*4)+1], int(rand()*12)+1, int(rand()*28)+1;
    }' > "$DATOS/clientes.csv"

    awk 'BEGIN {
        srand(2026);
        split("RECIBIDA,EN_PROGRESO,COMPLETADA,CANCELADA", e, ",");
        print "orden_id,cliente_id,estado,monto";
        for (i = 1; i <= 300; i++)
            printf "OS-%06d,CL-%05d,%s,%d\n", 500000 + i, 10000 + int(rand()*120) + 1, e[int(rand()*4)+1], int(rand()*90000) + 10000;
    }' > "$DATOS/ordenes.csv"

    for n in 1 2 3 4 5; do
        printf 'Contrato marco N %d\nCliente: CL-%05d\nVigencia: 12 meses\nSLA: 99.5%%\n' "$n" $((10000 + n)) \
            > "$DATOS/contratos/contrato_$n.txt"
    done

    printf 'empresa=NuevaNet\nsucursal=Melipilla\nmoneda=CLP\nretencion_dias=28\n' > "$DATOS/config/parametros.conf"
    head -c 524288 /dev/urandom > "$DATOS/reporte_mensual.dat"

    chmod -R u=rwX,go=rX "$DATOS"
}

# --- Logs de la aplicacion ---
generar_log() {
    # $1 archivo, $2 fecha base (AAAA-MM-DD), $3 tamano aproximado en MB
    awk -v fecha="$2" -v mb="$3" 'BEGIN {
        srand(length(fecha) + mb);
        split("INFO,INFO,INFO,WARN,ERROR", n, ",");
        split("som-api,crm-som", a, ",");
        split("GET /api/v1/ordenes -> 200,POST /api/v1/ordenes -> 201,PATCH /api/v1/ordenes -> 200,WEBHOOK entregado -> 200,healthcheck OK", m, ",");
        objetivo = mb * 1048576; total = 0;
        while (total < objetivo) {
            linea = sprintf("%s %02d:%02d:%02d %s %s %s orden=OS-%06d\n", fecha, int(rand()*24), int(rand()*60), int(rand()*60),
                            n[int(rand()*5)+1], a[int(rand()*2)+1], m[int(rand()*5)+1], 500000 + int(rand()*300));
            printf "%s", linea;
            total += length(linea);
        }
    }' > "$1"
}

crear_logs() {
    mensaje "Creando logs de prueba en $LOGS"
    rm -rf "$LOGS"
    mkdir -p "$LOGS"
    local i edad ep dia archivo
    for i in "${!EDADES_LOG[@]}"; do
        edad=${EDADES_LOG[$i]}
        ep=$(epoch_de "$edad")
        dia=$(date -d "@$ep" +%Y%m%d)
        archivo="$LOGS/app_$dia.log"
        generar_log "$archivo" "$(date -d "@$ep" +%F)" "${TAMANOS_LOG[$i]}"
        touch -d "@$ep" "$archivo"
    done
    chmod 755 "$LOGS"
    chmod 644 "$LOGS"/*.log
}

# --- Respaldos simulados ---
borrar_simulados() {
    [ -f "$CONTROL" ] || return 0
    local f
    while read -r f; do
        [ -n "$f" ] && rm -f "$DESTINO/$f" "$DESTINO/$f.sha256"
    done < "$CONTROL"
    rm -f "$CONTROL"
}

crear_respaldos_simulados() {
    mensaje "Creando respaldos simulados en $DESTINO"
    mkdir -p "$DESTINO" "$CONTROL_DIR"
    borrar_simulados

    local tmp i edad ep tipo nombre
    tmp=$(mktemp -d)
    mkdir -p "$tmp/srv/nuevanet/datos"
    cp -r "$DATOS/." "$tmp/srv/nuevanet/datos/"
    rm -f "$tmp/srv/nuevanet/datos/reporte_mensual.dat"

    for i in "${!EDADES_RESP[@]}"; do
        edad=${EDADES_RESP[$i]}
        tipo=${TIPOS_RESP[$i]}
        ep=$(epoch_de "$edad")
        nombre="respaldo_${tipo}_$(date -d "@$ep" +%Y%m%d)_080000.tar.gz"
        tar -czf "$DESTINO/$nombre" -C "$tmp" srv 2> /dev/null || error "no se pudo crear $nombre"
        ( cd "$DESTINO" && sha256sum "$nombre" > "$nombre.sha256" )
        touch -d "@$ep" "$DESTINO/$nombre" "$DESTINO/$nombre.sha256"
        echo "$nombre" >> "$CONTROL"
    done
    rm -rf "$tmp"
}

# --- Modo actividad: simula un dia de trabajo de NuevaNet ---
actividad() {
    [ -d "$DATOS" ] && [ -d "$LOGS" ] || error "primero prepare el ambiente: sudo bash $0"
    local hoy marca
    hoy=$(date +%Y%m%d)
    marca=$(date '+%F %T')
    mensaje "Simulando actividad del dia $hoy"
    printf 'OS-%06d,CL-%05d,RECIBIDA,%d\n' $(( (AHORA % 100000) + 600000 )) $(( 10001 + AHORA % 120 )) $(( 10000 + AHORA % 90000 )) >> "$DATOS/ordenes.csv"
    printf 'ultima_actualizacion=%s\n' "$marca" >> "$DATOS/config/parametros.conf"
    printf 'Novedad registrada el %s\n' "$marca" > "$DATOS/contratos/novedad_$hoy.txt"
    generar_log "$LOGS/app_$hoy.log" "$(date +%F)" 2
    chmod 644 "$LOGS/app_$hoy.log"
    mensaje "Modificados: ordenes.csv y config/parametros.conf. Nuevo: contratos/novedad_$hoy.txt y el log app_$hoy.log"
}

# --- Resumen ---
resumen() {
    echo
    mensaje "Ambiente preparado. Contenido generado:"
    echo
    echo "== $DATOS"
    find "$DATOS" -type f | sort
    echo
    echo "== $LOGS"
    ls -l --time-style=long-iso "$LOGS"
    echo
    echo "== $DESTINO (respaldos simulados)"
    ls -l --time-style=long-iso "$DESTINO"
    echo
    mensaje "Guarde este listado: es el estado inicial que se compara en la Fase 4."
}

# --- Programa principal ---
case "${1:-preparar}" in
    preparar)
        validar
        crear_datos
        crear_logs
        crear_respaldos_simulados
        resumen
        ;;
    actividad)
        validar
        actividad
        ;;
    ayuda|-h|--help)
        ayuda
        ;;
    *)
        echo "Opcion desconocida: $1" >&2
        ayuda
        exit 1
        ;;
esac
exit 0
