"""Generate configuration for WireGuard VPN node."""

import os
import textwrap

from ipalab_config.utils import save_file

base_config = {
    "image": "docker.io/procustodibus/wireguard",
    "cap_add": ["NET_RAW", "NET_ADMIN"],
}


def gen_config(_lab_config, base_dir, node, options):
    """Generate WireGuard configuration files."""
    # Get WireGuard configuration from options
    private_key = options.get("private_key", "")
    public_key = options.get("public_key", "")
    allowed_ip = options.get("allowed_ip", "0.0.0.0/0")
    listen_port = options.get("listen_port", 51822)

    # Validate required options
    if not private_key:
        raise ValueError("WireGuard role requires 'private_key' option")
    if not public_key:
        raise ValueError("WireGuard role requires 'public_key' option")

    # Create wireguard directory
    wg_dir = os.path.join(base_dir, "wireguard")
    os.makedirs(wg_dir, exist_ok=True)

    # Get node IP address for the Address field
    node_ip = node["networks"]["ipanet"]["ipv4_address"]

    # Generate WireGuard configuration
    wg_config = textwrap.dedent(f"""\
        [Interface]
        PrivateKey = {private_key}
        Address = {node_ip}/32
        ListenPort = {listen_port}

        PreUp = iptables -t nat -A POSTROUTING ! -o %i -j MASQUERADE

        [Peer]
        PublicKey = {public_key}
        AllowedIPs = {allowed_ip}
        """)

    # Save WireGuard configuration
    save_file(base_dir, "wireguard/wg0.conf", wg_config)

    # Update node configuration to mount the wireguard directory
    node.setdefault("volumes", []).append("${PWD}/wireguard:/etc/wireguard:Z")

    # We will not build the Wireguard image
    node.pop("build", None)
