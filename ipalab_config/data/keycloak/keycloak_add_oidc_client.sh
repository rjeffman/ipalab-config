#!/bin/bash -eu

SCRIPT_DIR="$(readlink -f "$(dirname "$0")")"
. "${SCRIPT_DIR}/keycloak_functions.sh"
. "${SCRIPT_DIR}/keycloak_config.sh"

usage() {
    cat <<EOF
usage: keycloak_add_oidc_client.sh [-h] IPASERVER OIDC_CLIENT_ID OIDC_PASSWORD
EOF
}

[ "${1:-}" == "-h" ] && usage && exit 0
[ $# -ne 3 ] && usage && die "All arguments must be provided"

IPASERVER="${1}"
OIDC_CLIENT_ID="${2}"
OIDC_PASSWORD="${3}"

echo Set truststore to use

podman exec "${KEYCLOAK_CONTAINER}" \
    /opt/keycloak/bin/kcreg.sh config truststore \
        --trustpass "${TRUSTPASSWORD}" \
        /opt/keycloak/conf/server.keystore

echo Login with kcreg

podman exec "${KEYCLOAK_CONTAINER}" \
    /opt/keycloak/bin/kcreg.sh config credentials \
        --server "${KEYCLOAK_URL}" \
        --realm master \
        --user "${ADMIN}" \
        --password "${PASSWORD}" \
    || die "Could not login with kcreg.sh"

echo Creating oidc_client ${OIDC_CLIENT_ID}

cat >/tmp/keycloak-client.json <<EOF
{
  "enabled" : true,
  "clientAuthenticatorType" : "client-secret",
  "redirectUris" : [ "https://${IPASERVER}/ipa/idp/*" ],
  "webOrigins" : [ "https://${IPASERVER}" ],
  "protocol" : "openid-connect",
  "attributes" : {
    "oauth2.device.authorization.grant.enabled" : "true",
    "oauth2.device.polling.interval": "5"
  }
}
EOF

podman cp \
    /tmp/keycloak-client.json \
    "${KEYCLOAK_CONTAINER}:/tmp/keycloak-client.json" \
    || die "Failed to copy OIDC client configuration"

podman exec "${KEYCLOAK_CONTAINER}" \
    /opt/keycloak/bin/kcreg.sh create \
        --server "${KEYCLOAK_URL}" \
        --realm master \
        -f /tmp/keycloak-client.json \
        -s clientId="${OIDC_CLIENT_ID=}" \
        -s secret="${OIDC_PASSWORD}" \
    || die "Could not create OIDC client."

