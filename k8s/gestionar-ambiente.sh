#!/usr/bin/env bash
# Gestion del ambiente de la Actividad 2.4.2 de CUY6142 (Duoc UC).
# Se ejecuta en el nodo servidor de k3s, desde la carpeta k8s del repositorio.
#
# Subcomandos:
#   claves [--forzar]   Crea el Secret editor-claves con una contrasena al azar por estudiante.
#                       Si ya existe, lo conserva (con --forzar, genera contrasenas nuevas).
#   claves ARCHIVO.csv  Crea el Secret editor-claves desde el archivo de la seccion: contrasena =
#                       RUT con digito verificador (modulo 11), sin puntos ni guion, K mayuscula.
#                       Cupos sin estudiante: contrasena al azar. Siempre reemplaza el Secret.
#   servicios           Genera y aplica los Services NodePort de cada estudiante
#                       (editor en 301NN, SOM en 302NN).
#   tabla [IP]          Genera la tabla de credenciales (URL del editor, de SOM y de Swagger, y contrasena)
#                       con la IP publica indicada o, sin IP, con la IP publica actual del servidor.
#   tabla ARCHIVO.csv [IP]  Genera la tabla de acceso por estudiante, SIN contrasenas (se publica en
#                       AVA), y aparte el archivo con las contrasenas de los cupos de reserva.
#   estado              Muestra nodos, pods y uso de memoria.
#   restablecer N       Deja el ambiente del estudiante N como nuevo (borra sus volumenes).
#   prueba-carga        Ejecuta carga_masiva.py en todos los pods a la vez y resume el resultado.
#
# Formato del archivo de la seccion (UTF-8, con encabezado; el RUT sin digito verificador):
#   N,rut,apellido_paterno,apellido_materno,nombres
#   1,16123463,Perez,Rojas,Juan Andres
# El archivo tiene datos personales: no se sube al repositorio (*.csv esta en .gitignore).
#
# Variables opcionales: NS (por defecto cuy6142) y CUPOS (por defecto 20).
set -euo pipefail

NS="${NS:-cuy6142}"
CUPOS="${CUPOS:-20}"
SECRET="editor-claves"
DIR="$(cd "$(dirname "$0")" && pwd)"
# Letras y numeros sin los que se confunden al leerlos (0/o, 1/l, i).
ALFABETO='abcdefghjkmnpqrstuvwxyz23456789'

uso() {
    sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'
}

generar_clave() {
    local clave
    clave="$(set +o pipefail; LC_ALL=C tr -dc "$ALFABETO" < /dev/urandom | head -c 8)"
    printf '%s' "$clave"
}

digito_verificador() {
    # Modulo 11: digitos de derecha a izquierda por 2,3,4,5,6,7 (y se repite); 11 - (suma mod 11).
    local rut="$1" suma=0 factor=2 i resto
    for (( i=${#rut}-1; i>=0; i-- )); do
        suma=$(( suma + ${rut:i:1} * factor ))
        factor=$(( factor == 7 ? 2 : factor + 1 ))
    done
    resto=$(( 11 - suma % 11 ))
    case "$resto" in
        11) printf '0' ;;
        10) printf 'K' ;;
        *) printf '%s' "$resto" ;;
    esac
}

leer_archivo() {
    # Valida el archivo de la seccion y deja los datos en los arreglos RUT[N] y NOMBRE[N].
    local archivo="$1" linea=0 n rut paterno materno nombres apellidos errores=0
    if [ ! -r "$archivo" ]; then
        echo "ERROR: no se puede leer el archivo ${archivo}" >&2
        exit 1
    fi
    declare -gA RUT=() NOMBRE=()
    while IFS=, read -r n rut paterno materno nombres || [ -n "${n:-}" ]; do
        linea=$((linea + 1))
        n="$(printf '%s' "$n" | LC_ALL=C tr -d '\r\357\273\277 ')"
        [ -z "$n" ] && continue
        [ "$linea" -eq 1 ] && [ "$n" = "N" ] && continue
        rut="$(printf '%s' "$rut" | tr -d '. \r')"
        rut="${rut%%-*}"
        nombres="$(printf '%s' "${nombres:-}" | tr -d '\r')"
        if ! [[ "$n" =~ ^[0-9]+$ ]] || [ "$n" -lt 1 ] || [ "$n" -gt "$CUPOS" ]; then
            echo "ERROR linea ${linea}: N debe ser un numero entre 1 y ${CUPOS} (valor: ${n})" >&2
            errores=$((errores + 1)); continue
        fi
        if ! [[ "$rut" =~ ^[0-9]{7,8}$ ]]; then
            echo "ERROR linea ${linea}: el RUT debe tener 7 u 8 digitos, sin digito verificador (valor: ${rut})" >&2
            errores=$((errores + 1)); continue
        fi
        if [ -n "${RUT[$n]:-}" ]; then
            echo "ERROR linea ${linea}: el numero ${n} esta repetido" >&2
            errores=$((errores + 1)); continue
        fi
        RUT[$n]="$rut"
        # El apellido materno puede venir vacio.
        apellidos="$(printf '%s %s' "$paterno" "$materno" | sed 's/ *$//')"
        NOMBRE[$n]="${apellidos}, ${nombres}"
    done < "$archivo"
    if [ "$errores" -gt 0 ]; then
        echo "El archivo tiene ${errores} error(es). Corrijalo y repita." >&2
        exit 1
    fi
    echo "Archivo ${archivo}: ${#RUT[@]} estudiantes."
}

ip_publica_servidor() {
    # Servicio de metadatos de EC2 (IMDSv2): primero pide un token y luego la IP publica.
    local token
    token="$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60")" || return 1
    curl -sf -H "X-aws-ec2-metadata-token: ${token}" \
        "http://169.254.169.254/latest/meta-data/public-ipv4"
}

clave_de() {
    kubectl -n "$NS" get secret "$SECRET" -o go-template="{{index .data \"est-$1\"}}" | base64 -d
}

cmd_claves() {
    local primero="${1:-}" args=() n
    if [ -n "$primero" ] && [ "$primero" != "--forzar" ]; then
        # Modo archivo de la seccion: contrasena = RUT con digito verificador.
        leer_archivo "$primero"
        for n in $(seq 1 "$CUPOS"); do
            if [ -n "${RUT[$n]:-}" ]; then
                args+=("--from-literal=est-${n}=${RUT[$n]}$(digito_verificador "${RUT[$n]}")")
            else
                args+=("--from-literal=est-${n}=$(generar_clave)")
            fi
        done
        kubectl -n "$NS" create secret generic "$SECRET" "${args[@]}" --dry-run=client -o yaml \
            | kubectl apply -f -
        echo "Secret ${SECRET} listo: ${#RUT[@]} estudiantes y $((CUPOS - ${#RUT[@]})) cupos de reserva."
        echo "Los editores leen la contrasena al arrancar. Si los pods ya existen, reinicielos:"
        echo "  kubectl -n ${NS} rollout restart statefulset est"
        return 0
    fi

    if kubectl -n "$NS" get secret "$SECRET" > /dev/null 2>&1 && [ "$primero" != "--forzar" ]; then
        echo "El Secret ${SECRET} ya existe: se conservan las contrasenas."
        echo "Para generar contrasenas nuevas: $0 claves --forzar"
        return 0
    fi
    for n in $(seq 1 "$CUPOS"); do
        args+=("--from-literal=est-${n}=$(generar_clave)")
    done
    kubectl -n "$NS" create secret generic "$SECRET" "${args[@]}" --dry-run=client -o yaml \
        | kubectl apply -f -
    echo "Secret ${SECRET} listo con ${CUPOS} contrasenas."
    if [ "$primero" = "--forzar" ]; then
        echo "Los editores leen la contrasena al arrancar. Para aplicar las nuevas, reinicie los pods:"
        echo "  kubectl -n ${NS} rollout restart statefulset est"
    fi
}

cmd_servicios() {
    local archivo="${DIR}/servicios-generados.yaml" n

    : > "$archivo"
    for n in $(seq 1 "$CUPOS"); do
        cat >> "$archivo" <<EOF
---
apiVersion: v1
kind: Service
metadata:
  name: est-${n}
  namespace: ${NS}
  labels:
    app.kubernetes.io/name: est
spec:
  type: NodePort
  selector:
    statefulset.kubernetes.io/pod-name: est-${n}
  ports:
    - name: editor
      port: 8080
      targetPort: editor
      nodePort: $((30100 + n))
    - name: som
      port: 8081
      targetPort: som
      nodePort: $((30200 + n))
EOF
    done
    kubectl apply -f "$archivo"
    echo "Services aplicados. Definicion guardada en ${archivo}"
}

obtener_ip() {
    local ip="${1:-}"
    if [ -z "$ip" ]; then
        ip="$(ip_publica_servidor)" || {
            echo "ERROR: no se pudo obtener la IP publica. Indiquela al final del comando." >&2
            exit 1
        }
    fi
    printf '%s' "$ip"
}

cmd_tabla_archivo() {
    local archivo_csv="$1" ip n marca tabla reservas estudiante
    leer_archivo "$archivo_csv"
    ip="$(obtener_ip "${2:-}")"
    kubectl -n "$NS" get secret "$SECRET" > /dev/null
    marca="$(date +%Y%m%d-%H%M)"
    tabla="${DIR}/tabla-acceso-${marca}.md"
    reservas="${DIR}/reservas-${marca}.md"
    {
        echo "# Tabla de acceso - Actividad 2.4.2 CUY6142"
        echo
        echo "Busque su nombre. La contrasena de su editor es su RUT con digito verificador, sin puntos"
        echo "ni guion (si termina en K, en mayuscula). Use solo su fila."
        echo
        echo "| N | Estudiante | TU_URL_EDITOR (navegador) | TU_URL_SOM (solo Postman) | TU_URL_SWAGGER (navegador) |"
        echo "| --- | --- | --- | --- | --- |"
    } > "$tabla"
    {
        echo "# Cupos de reserva - Actividad 2.4.2 CUY6142 (uso docente, no publicar)"
        echo
        echo "| N | Contrasena del editor |"
        echo "| --- | --- |"
    } > "$reservas"
    for n in $(seq 1 "$CUPOS"); do
        estudiante="${NOMBRE[$n]:-Reserva}"
        printf '| %02d | %s | http://%s:%d | http://%s:%d/api/v2 | http://%s:%d/api/v2/docs |\n' \
            "$n" "$estudiante" "$ip" $((30100 + n)) "$ip" $((30200 + n)) "$ip" $((30200 + n)) >> "$tabla"
        if [ -z "${RUT[$n]:-}" ]; then
            printf '| %02d | %s |\n' "$n" "$(clave_de "$n")" >> "$reservas"
        fi
    done
    cat "$tabla"
    echo
    echo "Tabla para publicar en AVA: ${tabla}"
    echo "Cupos de reserva (solo docente): ${reservas}"
}

cmd_tabla() {
    local primero="${1:-}" ip n clave archivo
    if [[ "$primero" == *.csv ]]; then
        cmd_tabla_archivo "$primero" "${2:-}"
        return 0
    fi
    ip="$(obtener_ip "$primero")"
    kubectl -n "$NS" get secret "$SECRET" > /dev/null
    archivo="${DIR}/credenciales-$(date +%Y%m%d-%H%M).md"
    {
        echo "# Credenciales del ambiente CUY6142 - Actividad 2.4.2"
        echo
        echo "Generada el $(date '+%d/%m/%Y %H:%M'). IP publica del servidor: ${ip}"
        echo
        echo "Cada estudiante usa SOLO su fila. Los nombres de columna son los de la Actividad 2.4.2."
        echo
        echo "| N | TU_URL_EDITOR (navegador) | TU_URL_SOM (solo Postman) | TU_URL_SWAGGER (navegador) | Contraseña |"
        echo "| --- | --- | --- | --- | --- |"
        for n in $(seq 1 "$CUPOS"); do
            clave="$(clave_de "$n")"
            if [ -z "$clave" ]; then
                echo "ERROR: el Secret ${SECRET} no tiene la clave est-${n}. Ejecute: $0 claves --forzar" >&2
                exit 1
            fi
            printf '| %02d | http://%s:%d | http://%s:%d/api/v2 | http://%s:%d/api/v2/docs | %s |\n' \
                "$n" "$ip" $((30100 + n)) "$ip" $((30200 + n)) "$ip" $((30200 + n)) "$clave"
        done
    } > "$archivo"
    cat "$archivo"
    echo
    echo "Tabla guardada en ${archivo}"
}

cmd_estado() {
    echo "== Nodos =="
    kubectl get nodes -o wide
    echo
    echo "== Pods de estudiantes (nodo, estado y reinicios) =="
    kubectl -n "$NS" get pods -o wide
    echo
    echo "== Memoria y CPU por nodo =="
    kubectl top nodes || echo "(metrics-server aun no tiene datos; espere un minuto)"
}

cmd_restablecer() {
    local n="${1:-}" respuesta
    if ! [[ "$n" =~ ^[0-9]+$ ]] || [ "$n" -lt 1 ] || [ "$n" -gt "$CUPOS" ]; then
        echo "Uso: $0 restablecer N   (N entre 1 y ${CUPOS})" >&2
        exit 1
    fi
    echo "Se borraran la carpeta personal y los datos de SOM del estudiante ${n} (pod est-${n})."
    read -r -p "Escriba SI para continuar: " respuesta
    if [ "$respuesta" != "SI" ]; then
        echo "Cancelado."
        return 0
    fi
    kubectl -n "$NS" delete pvc "home-est-${n}" "datos-som-est-${n}" --wait=false
    kubectl -n "$NS" delete pod "est-${n}" --wait=true
    kubectl -n "$NS" wait --for=delete "pvc/home-est-${n}" "pvc/datos-som-est-${n}" --timeout=120s || true
    # El pod que el StatefulSet creo mientras se borraban los volumenes se elimina otra vez,
    # para que el nuevo se cree con volumenes nuevos.
    kubectl -n "$NS" delete pod "est-${n}" --wait=true --ignore-not-found
    echo "Ambiente del estudiante ${n} restablecido. Revise: kubectl -n ${NS} get pod est-${n}"
}

cmd_prueba_carga() {
    local carpeta n inicio fin creadas
    carpeta="${DIR}/prueba-carga-$(date +%Y%m%d-%H%M)"
    mkdir -p "$carpeta"
    echo "Ejecutando carga_masiva.py en ${CUPOS} pods a la vez. Registros en ${carpeta}"
    inicio=$(date +%s)
    for n in $(seq 1 "$CUPOS"); do
        kubectl -n "$NS" exec "est-${n}" -c editor -- \
            /home/coder/Formativa242/.venv/bin/python /home/coder/Formativa242/carga_masiva.py \
            > "${carpeta}/est-${n}.log" 2>&1 &
    done
    wait
    fin=$(date +%s)
    echo
    for n in $(seq 1 "$CUPOS"); do
        creadas="$(grep -h 'Total de ordenes creadas' "${carpeta}/est-${n}.log" || echo 'SIN RESULTADO')"
        printf 'est-%-3s %s\n' "$n" "$creadas"
    done
    echo
    echo "Tiempo total: $((fin - inicio)) segundos."
}

subcomando="${1:-}"
shift || true
case "$subcomando" in
    claves) cmd_claves "$@" ;;
    servicios) cmd_servicios ;;
    tabla) cmd_tabla "$@" ;;
    estado) cmd_estado ;;
    restablecer) cmd_restablecer "$@" ;;
    prueba-carga) cmd_prueba_carga ;;
    *) uso; exit 1 ;;
esac
