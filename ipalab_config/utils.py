"""ipalab_config utility functions."""

import sys
import socket
import ipaddress


def die(msg, err=1):
    """Display message to stderr stream and exit program with error."""
    print(msg, file=sys.stderr)
    sys.exit(err)


def ensure_fqdn(hostname, domain):
    """Ensure hostame is a FQDN."""
    return hostname if "." in hostname else f"{hostname}.{domain}"


def get_hostname(config, name, domain):
    """Ensure hostname from config is FQDN."""
    hostname = config.get("hostname", name)
    return ensure_fqdn(hostname, domain)


def is_ip_address(addr):
    """Check if a given string represents an IP address."""
    try:
        socket.inet_pton(socket.AF_INET, addr)
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, addr)
        except OSError:
            return False
    return True


def get_ip_address_generator(for_cidr=None):
    """Create an IP address generator given a network CIDR."""
    network = ipaddress.IPv4Interface(for_cidr or "192.168.159.0/24").network
    generator = network.hosts()
    next(generator)  # assume first IP is the gateway IP address.
    return generator
