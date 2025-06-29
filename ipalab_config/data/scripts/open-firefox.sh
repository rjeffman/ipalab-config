#!/bin/bash

SCRIPTDIR="$(dirname $(realpath "$0"))"
TOPDIR="$(dirname "${SCRIPTDIR}")"

die() {
    >&2 echo $*
    exit 1
}

detach() {
    nohup "$@" >/dev/null 2>&1 </dev/null &
}

usage() {
    cat <<EOF
usage: $(basename "$0") [-c CONTAINER] [-p PROFILE] [-r] [URL]"

Open URL in Firefox with the given profile (defaults to 'ipalab-profile').

Options:

    -p PROFILE     use the given profile name
    -c CONTAINER   Import IPA CA root from CONTAINER
    -r             remove the profile

EOF
}

copy_certificate() {
    YQ="$(command -v yq)"
    ipa_ca_node="${1:-}"
    if [ -z "$ipa_ca_node" ] && [ -n "${YQ}" ]
    then
        echo "Containers on this compose:"
        yq ".services | keys" < "${TOPDIR}/compose.yml"
        read -p "Which compose to copy CA certs from? " ipa_ca_node
    fi

    CERTUTIL="$(command -v certutil)"
    if [ -n "${CERTUTIL}" ] && [ -n "${ipa_ca_node}" ]
    then
        certutil -N -d "${CONTAINER_PROFILE_DIR}" --empty-password
        podman cp ${ipa_ca_node}:/etc/ipa/ca.crt "${CONTAINER_PROFILE_DIR}/ca.crt"
        certutil -A -i "${CONTAINER_PROFILE_DIR}/ca.crt" -d "${CONTAINER_PROFILE_DIR}" -n "Certificate Authority - IPA dev ${profile_name}" -t "CT,C,"
    fi
}


MOZILLA_PROFILES="${HOME}/.mozilla/firefox/profiles.ini"

profile_name="ipalab-profile"
cmd="open"
ipa_ca_node=""

while getopts ":hc:p:r" option
do
    case "${option}" in
        h) usage && exit 0 ;;
        c) ipa_ca_node="${OPTARG}" ;;
        p) profile_name="${OPTARG}" ;;
        r) cmd="remove" ;;
        *) die -u "Invalid option: ${OPTARG}" ;;
    esac
done
shift "$((OPTIND - 1))"

[ $# -gt 1 ] && die "Only one URL can be used. (Didn't you forgot '-p'?)"

echo "Using profile ${profile_name}"

CONTAINER_PROFILE_DIR="${HOME}/.mozilla/firefox/${profile_name}"

if [ "$cmd" == "remove" ]
then
    sed -i "/^\# start - Added by ipalab-config: ${profile_name}$/,/^\# end - Added by ipalab-config: ${profile_name}/d" "${MOZILLA_PROFILES}"
    rm -rf "${CONTAINER_PROFILE_DIR}"
    exit
fi

if [ -d "${CONTAINER_PROFILE_DIR}" ]
then
    [ -z "${ipa_ca_node:-}" ] || copy_certificate "${ipa_ca_node}"
else
    mkdir "${CONTAINER_PROFILE_DIR}"
    copy_certificate "${ipa_ca_node:-}"
fi

if ! grep -q "Name=${profile_name}" "${MOZILLA_PROFILES}"
then
    echo "Creating Firefox profile: ${profile_name}"

    next_profile=$(echo $(($(cat "${MOZILLA_PROFILES}" | sed -n 's/\[Profile\([^\]]*\)\]/\1/p' | sort -n | tail -n 1) + 1)))

    cat >> "${MOZILLA_PROFILES}" <<EOF
# start - Added by ipalab-config: ${profile_name}
[Profile${next_profile}]
Name=${profile_name}
IsRelative=1
Path=${profile_name}
# end - Added by ipalab-config: ${profile_name}
EOF

fi

[ -z "$@" ] || detach podman unshare --rootless-netns firefox -P "$profile_name" --new-window "$@"
