"""Generate configuration for Samba AD DC."""

import os
from ipalab_config.utils import copy_resource_files

base_config = {
    "image": "localhost/samba-addc",
    "build": {
        "context": "containerfiles",
        "dockerfile": "external-nodes",
        "args": {"packages": "systemd"},
    },
    "command": "/usr/sbin/init",
}


def gen_config(_lab_config, base_dir, _node, _options):
    """Update node configuration."""
    copy_resource_files(
        "playbooks/deploy_addc.yml", os.path.join(base_dir, "playbooks")
    )
