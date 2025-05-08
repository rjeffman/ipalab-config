"""Generate configuration for external host: Keycloak"""

import textwrap

from ipalab_config.utils import copy_helper_files, save_file

base_config = {
    "image": "localhost/keycloak",
    "build": {
        "context": "keycloak",
        "dockerfile": "Containerfile",
        "args": {"hostname": "{hostname}"},
    },
    "environment": {
        "KC_BOOTSTRAP_ADMIN_USERNAME": "{admin_username}",
        "KC_BOOTSTRAP_ADMIN_PASSWORD": "{admin_password}",
        "KC_HOSTNAME": "{hostname}",
    },
    "entrypoint": "/opt/keycloak/bin/kc.sh start",
}


def gen_config(_lab_config, base_dir, node, options):
    """Update node configuration."""

    def apply_formatting(config_section, keys, defaults):
        for key in keys:
            config_section[key] = config_section[key].format(**defaults)
        return config_section

    defaults = {
        "admin_username": "admin",
        "admin_password": "secret123",
        "oidc_password": "secret123",
        "hostname": node.get("hostname", "localhost"),
    } | (options or {})

    # Then in gen_config:
    env_keys = [
        "KC_BOOTSTRAP_ADMIN_USERNAME",
        "KC_BOOTSTRAP_ADMIN_PASSWORD",
        "KC_HOSTNAME",
    ]

    node["environment"] = apply_formatting(
        node["environment"], env_keys, defaults
    )

    node["build"]["args"] = apply_formatting(
        node["build"]["args"], ["hostname"], defaults
    )

    copy_helper_files(base_dir, "keycloak")

    keycloak_config = textwrap.dedent(
        f"""\
    ADMIN="{defaults['admin_username']}"
    PASSWORD="{defaults['admin_password']}"
    OIDCPASSWORD="{defaults['oidc_password']}"
    KEYCLOAK="{node.get('hostname', 'localhost1')}"
    KEYCLOAK_CONTAINER="{node['container_name']}"

    KEYCLOAK_URL="https://${{KEYCLOAK}}:8443"
    TRUSTPASSWORD="password"
    """
    )

    save_file(base_dir, "keycloak/keycloak_config.sh", keycloak_config)
