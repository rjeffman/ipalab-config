"""ipalab_config utility functions."""

import sys


def die(msg, err=1):
    """Display message to stderr stream and exit program with error."""
    print(msg, file=sys.stderr)
    sys.exit(err)


def get_hostname(config, name, domain):
    """Ensure hostname from config is FQDN."""
    hostname = config.get("hostname", f"{name}.{domain}")
    if not "." in hostname:
        hostname = f"{hostname}.{domain}"
    return hostname
