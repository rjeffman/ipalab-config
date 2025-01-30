"""ipalab_config utility functions."""

import os
import shutil
import sys
import socket
import ipaddress
import importlib.resources


def die(msg, err=1):  # pragma: no cover
    """Display message to stderr stream and exit program with error."""
    print(msg, file=sys.stderr)
    return err


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


def get_service_ip_address(service):
    """Return the compose service IP address."""
    return service["networks"]["ipanet"]["ipv4_address"]


def copy_extra_files(files, target_dir):
    """Copy files to the target directory."""
    os.makedirs(target_dir, exist_ok=True)
    for source in files:
        filename = os.path.basename(source)
        shutil.copyfile(source, os.path.join(target_dir, filename))


def copy_resource_files(files, target_dir):
    """Copy ipalab-config resource files to target directory."""
    os.makedirs(target_dir, exist_ok=True)
    if not isinstance(files, (list, tuple)):
        files = [files]
    for source in files:
        filename = os.path.join(
            importlib.resources.files("ipalab_config"), "data", source
        )
        shutil.copyfile(
            filename, os.path.join(target_dir, os.path.basename(filename))
        )


def copy_helper_files(base_dir, directory, source=None):
    """Copy directory helper files to target directory"""
    target_dir = os.path.join(base_dir, directory)
    os.makedirs(target_dir, exist_ok=True)

    if source is None:
        source = os.path.join(
            importlib.resources.files("ipalab_config"), "data"
        )
    origin = os.path.join(source, directory)
    shutil.copytree(origin, target_dir, dirs_exist_ok=True)


def save_file(base_dir, filename, data):
    """Write data to an output file."""
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, filename), "w") as out:
        out.write(data)
