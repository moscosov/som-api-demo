#!/bin/bash
# Datos de usuario (user data) de los nodos agente de k3s -- CUY6142, Actividad 2.4.2.
# EC2 ejecuta este script como root una sola vez, en el primer arranque de cada agente.
# Instala k3s en modo agente y lo une al servidor por su IP PRIVADA.
#
# Antes de pegarlo en la consola EC2, reemplace los tres valores entre < >.
export K3S_URL="https://<IP_PRIVADA_SERVIDOR>:6443"
export K3S_TOKEN="<TOKEN_K3S>"
export INSTALL_K3S_VERSION="<VERSION_K3S>"
curl -sfL https://get.k3s.io | sh -
