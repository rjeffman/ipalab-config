#!/bin/bash -eu

usage() {
    cat <<EOF
usage: keycloak_add_user USER_LOGIN USER_EMAIL USER_PASSWORD
EOF
}

SCRIPT_DIR="$(readlink -f "$(dirname "$0")")"
. "${SCRIPT_DIR}/keycloak_functions.sh"
. "${SCRIPT_DIR}/keycloak_config.sh"

[ $# -eq 0 ] && usage && exit 0
[ "$1" == "--help" ] || [ "$1" == "-h" ] && usage && exit 0
[ $# -ne 3 ] && usage && die "All arguments are necessary"

USER_LOGIN="$1"
USER_EMAIL="$2"
USER_PASSWORD="$3"

echo Login with kcadm

podman exec ${KEYCLOAK_CONTAINER} \
    /opt/keycloak/bin/kcadm.sh config truststore \
        --trustpass ${TRUSTPASSWORD} \
        /opt/keycloak/conf/server.keystore

podman exec ${KEYCLOAK_CONTAINER} \
    /opt/keycloak/bin/kcadm.sh config credentials \
        --server "${KEYCLOAK_URL}" \
        --realm master \
        --user "${ADMIN}" \
        --password "${PASSWORD}" \
    || die "Could not login with kcadm"

echo Adding user ${USER_EMAIL}

podman exec ${KEYCLOAK_CONTAINER} \
    /opt/keycloak/bin/kcadm.sh create users --realm=master \
        -s username=${USER_LOGIN} \
        -s enabled=true \
        -s email="${USER_EMAIL}" \
        -s emailVerified=true \
        --server "${KEYCLOAK_URL}" \
    || die "Could not create user '${USER_EMAIL}'"

echo Setting user password

podman exec ${KEYCLOAK_CONTAINER} \
    /opt/keycloak/bin/kcadm.sh set-password --realm=master \
        --username "${USER_LOGIN}" \
        --new-password "${USER_PASSWORD}" \
        --server "${KEYCLOAK_URL}" \
    || die "Could not set password for '${USER_EMAIL}'"

