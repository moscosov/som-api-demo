#!/usr/bin/env bash
# Gestion del ambiente de la Actividad 2.4.2 de CUY6142 (Duoc UC).
# Se ejecuta en el nodo servidor de k3s, desde la carpeta k8s del repositorio.
#
# Subcomandos:
#   claves [--forzar]   Crea el Secret editor-claves con una contrasena al azar por estudiante.
#                       Si ya existe, lo conserva (con --forzar, genera contrasenas nuevas).
#   servicios           Genera y aplica los Services NodePort de cada estudiante
#                       (editor en 301NN, SOM en 302NN).
#   tabla [IP]          Genera la tabla de credenciales con la IP publica indicada o, sin IP,
#                       con la IP publica actual del servidor.
#   estado              Muestra nodos, pods y uso de memoria.
#   restablecer N       Deja el ambiente del estudiante N como nuevo (borra sus volumenes).
#   prueba-carga        Ejecuta carga_masiva.py en todos los pods a la vez y resume el resultado.
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
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
}

generar_clave() {
    local clave
    clave="$(set +o pipefail; LC_ALL=C tr -dc "$ALFABETO" < /dev/urandom | head -c 8)"
    printf '%s' "$clave"
}

ip_publica_servidor() {
    # Servicio de metadatos de EC2 (IMDSv2): primero pide un token y luego la IP publica.
    local token
    token="$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60")" || return 1
    curl -sf -H "X-aws-ec2-metadata-token: ${token}" \
        "http://169.254.169.254/latest/meta-data/public-ipv4"
}

cmd_claves() {
    local forzar="${1:-}"
    if kubectl -n "$NS" get secret "$SECRET" > /dev/null 2>&1 && [ "$forzar" != "--forzar" ]; then
        echo "El Secret ${SECRET} ya existe: se conservan las contrasenas."
        echo "Para generar contrasenas nuevas: $0 claves --forzar"
        return 0
    fi
    local args=() n
    for n in $(seq 1 "$CUPOS"); do
        args+=("--from-literal=est-${n}=$(generar_clave)")
    done
    kubectl -n "$NS" create secret generic "$SECRET" "${args[@]}" --dry-run=client -o yaml \
        | kubectl apply -f -
    echo "Secret ${SECRET} listo con ${CUPOS} contrasenas."
    if [ "$forzar" = "--forzar" ]; then
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

cmd_tabla() {
    local ip="${1:-}" n clave archivo
    if [ -z "$ip" ]; then
        ip="$(ip_publica_servidor)" || {
            echo "ERROR: no se pudo obtener la IP publica. Indiquela: $0 tabla <IP>" >&2
            exit 1
        }
    fi
    kubectl -n "$NS" get secret "$SECRET" > /dev/null
    archivo="${DIR}/credenciales-$(date +%Y%m%d-%H%M).md"
    {
        echo "# Credenciales del ambiente CUY6142 - Actividad 2.4.2"
        echo
        echo "Generada el $(date '+%d/%m/%Y %H:%M'). IP publica del servidor: ${ip}"
        echo
        echo "| N | Editor (navegador) | SOM (variable base de Postman) | Contrasena del editor |"
        echo "| --- | --- | --- | --- |"
        for n in $(seq 1 "$CUPOS"); do
            clave="$(kubectl -n "$NS" get secret "$SECRET" \
                -o go-template="{{index .data \"est-${n}\"}}" | base64 -d)"
            if [ -z "$clave" ]; then
                echo "ERROR: el Secret ${SECRET} no tiene la clave est-${n}. Ejecute: $0 claves --forzar" >&2
                exit 1
            fi
            printf '| %02d | http://%s:%d | http://%s:%d/api/v2 | %s |\n' \
                "$n" "$ip" $((30100 + n)) "$ip" $((30200 + n)) "$clave"
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
