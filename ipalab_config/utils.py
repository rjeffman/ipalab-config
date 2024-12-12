"""ipalab_config utility functions."""

import sys
import socket


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
    try:
        socket.inet_pton(socket.AF_INET, addr)
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, addr)
        except OSError:
            return False
    return True
