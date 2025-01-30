"""Generate configuration for Samba AD DC."""

import os
from ipalab_config.utils import copy_resource_files


def gen_addc_config(_lab_config, base_dir, _node, _options):
    """Update node configuration."""
    copy_resource_files(
        "samba-addc/deploy_addc.yml", os.path.join(base_dir, "playbooks")
    )
