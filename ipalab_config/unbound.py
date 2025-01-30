"""Generate configuration for the Unbound nameserver."""

import os
import ipaddress
import textwrap

from ipalab_config.utils import copy_helper_files, copy_extra_files, save_file


def gen_unbound_config(lab_config, base_dir, _node, options):
    """Generate configuration for external DNS container."""
    subnet = lab_config["subnet"]
    domains = []
    networks = [ipaddress.IPv4Interface(subnet).network]
    zone_files = []

    zone_template = textwrap.dedent(
        """\
    auth-zone:
        name: {name}
        zonefile: /etc/unbound/zones/{filename}
        for-downstream: yes
        for-upstream: no
    """
    )

    copy_helper_files(base_dir, "unbound")

    zone_data = []
    for zone in options.get("zones", []):
        filename = zone["file"]
        zone_files.append(filename)
        if "name" in zone:
            name = zone["name"]
            domains.append(name)
        else:
            network = ipaddress.IPv4Interface(zone["reverse_ip"]).network
            networks.append(network)
            name = network[0].reverse_pointer.split(".", 1)[1]
        zone_data.append({"name": name, "filename": os.path.basename(filename)})

    save_file(
        base_dir,
        "unbound/zones.conf",
        "\n".join(zone_template.format(**zone) for zone in zone_data),
    )
    save_file(
        base_dir,
        "unbound/domains",
        "\n".join(f"private-domain: {domain}" for domain in domains),
    )
    save_file(
        base_dir,
        "unbound/access_control",
        "\n".join(
            f"access-control: {network} allow" for network in set(networks)
        ),
    )

    copy_extra_files(zone_files, os.path.join(base_dir, "unbound/zones"))
