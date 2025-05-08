#!/bin/bash -eu

SCRIPT_DIR="$(readlink -f "$(dirname "$0")")"
. "${SCRIPT_DIR}/keycloak_functions.sh"
. "${SCRIPT_DIR}/keycloak_config.sh"

usage() {
    cat <<EOF
usage: truest_keycloak.sh [-h] CONTAINER_NAME
EOF
}

[ "${1:-}" == "-h" ] && usage && exit 0
[ $# -ne 1 ] && usage && die "Missing container name"

CONTAINER_NAME="$1"
shift

podman cp \
    "${KEYCLOAK_CONTAINER}:/opt/keycloak/conf/cert.pem" \
    "${CONTAINER_NAME}:/etc/pki/ca-trust/source/anchors/keycloak.pem"
podman exec "${CONTAINER_NAME}" /usr/bin/update-ca-trust extract
