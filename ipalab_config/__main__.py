"""Generate compose and inventory configuration for a FreeIPA cluster."""

import argparse
import os
import sys

from ruamel.yaml import YAML

from ipalab_config import __version__
from ipalab_config.utils import (
    die,
    copy_extra_files,
    copy_helper_files,
    save_file,
    get_service_ip_address,
)
from ipalab_config.compose import gen_compose_data
from ipalab_config.inventory import gen_inventory_data
from ipalab_config.unbound import gen_unbound_config
from ipalab_config.addc import gen_addc_config


def parse_arguments():
    """Parse command line arguments."""
    opt_parser = argparse.ArgumentParser(
        prog="ipa-lab-config",
        description=(
            "Generate compose and inventory conifguration for FreeIPA lab."
        ),
    )
    opt_parser.add_argument("CONFIG", help="Lab description")
    opt_parser.add_argument("--version", action="version", version=__version__)
    opt_parser.add_argument(
        "-o",
        "--output",
        dest="OUTPUT",
        metavar="OUTPUT",
        default=None,
        help="Output directory",
    )
    opt_parser.add_argument(
        "-f",
        "--file",
        dest="RECIPES",
        metavar="CONTAINERFILE",
        action="append",
        default=[],
        help=(
            "Containerfile to use for creating images. "
            "May be used more than once for multiple files."
        ),
    )
    opt_parser.add_argument(
        "-p",
        "--playbook",
        dest="PLAYBOOKS",
        metavar="PLAYBOOKS",
        action="append",
        default=[],
        help=(
            "Add playbook to the resulting configuration 'playbooks' "
            "directory. When adding a directory, all 'yml' or 'yaml' "
            "files in the directory, searched recursively will be copied. "
            "May be used more than once for multiple files."
        ),
    )
    opt_parser.add_argument(
        "-d",
        "--distro",
        dest="DISTRO",
        metavar="DISTRO",
        default="fedora-latest",
        nargs="?",
        choices=["fedora-latest", "fedora-rawhide", "c10s", "c9s", "c8s"],
        help=(
            "Define default distro. Valid values are 'fedora-latest', "
            "'fedora-rawhide', 'c10s', 'c9s', 'c8s'. Defaults to "
            "'fedora-latest'."
        ),
    )
    opt_parser.add_argument(
        "--debug",
        action="store_true",
        help="Run ipalab-config in debug mode.",
    )
    return opt_parser.parse_args()


def save_data(yaml, base_dir, filename, yamldata):
    """Save YAML data as a YAML file."""
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, filename), "w") as out:
        yaml.dump(yamldata, out)


def gen_external_node_configuration(lab_config, base_dir, compose_config):
    """Generate configuration for external nodes"""
    for _, node_data in compose_config["services"].items():
        external_data = node_data.pop("external_node", None)
        if external_data:
            role = external_data.get("role", "none").lower()
            options = external_data.get("options", {})
            # update dns on nodes
            if "dns" in node_data:
                dns = node_data["dns"]
                if dns in lab_config["nodes"]:
                    dns = lab_config["nodes"][dns]
                elif dns in compose_config["services"]:
                    dns = get_service_ip_address(
                        compose_config["services"][dns]
                    )
                node_data["dns"] = dns
                if not node_data.get("dns_search"):
                    node_data.pop("dns_search", None)
            else:
                node_data.pop("dns_search", None)
            # update roles
            roles = {
                "dns": gen_unbound_config,
                "addc": gen_addc_config,
            }
            config_fn = roles.get(role)
            if config_fn:
                config_fn(lab_config, base_dir, node_data, options)
            else:
                raise ValueError(f"Invalid role: '{role}'")


def gen_optional_files(lab_config, base_dir, yaml):
    """Save optional 'misc' files."""
    # save /etc/hosts file patch
    save_file(
        base_dir,
        "hosts",
        f"\n# ipalab-config hosts for '{lab_config['lab_name']}'\n"
        + "\n".join(
            [
                f"{v:18s}{k.replace('_', '.')}"
                for k, v in lab_config.get("nodes", {}).items()
            ]
        ),
    )

    # add Ansible Galaxy requirements.yml
    save_data(
        yaml,
        base_dir,
        "requirements.yml",
        {
            "collections": [
                {"name": "containers.podman"},
                {"name": "freeipa.ansible_freeipa"},
            ]
        },
    )


def save_containers_data(lab_config, base_dir, args):
    """Copy containerfiles to result directory."""
    copy_helper_files(base_dir, "containerfiles")

    containerfiles = [
        (
            os.path.realpath(
                os.path.join(
                    os.path.dirname(os.path.realpath(args.CONFIG)),
                    containerfile,
                )
            )
            if not containerfile.startswith("/")
            else containerfile
        )
        for containerfile in lab_config.get("containerfiles", [])
    ]
    copy_extra_files(
        containerfiles + args.RECIPES,
        os.path.join(base_dir, "containerfiles"),
    )


def save_ansible_data(_lab_config, base_dir, args):
    """Copy Ansible playbooks to result directory."""
    copy_helper_files(base_dir, "playbooks")

    plays = []
    for play in args.PLAYBOOKS:
        if os.path.isfile(play):
            plays.append(play)
        if os.path.isdir(play):
            plays.extend(
                [
                    os.path.join(dirname, name)
                    for dirname, _, filenames in os.walk(play)
                    for name in filenames
                    if name.endswith(".yml") or name.endswith(".yaml")
                ]
            )

    copy_extra_files(plays, os.path.join(base_dir, "playbooks"))


def generate_ipalab_configuration():
    """Generate compose and inventory."""
    args = parse_arguments()
    yaml = YAML()
    yaml.explicit_start = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    # pylint: disable=unspecified-encoding
    with open(args.CONFIG, "r") as config_file:
        data = yaml.load(config_file.read())

    labname = data.setdefault("lab_name", "ipa-lab")
    base_dir = args.OUTPUT or labname

    # set default values
    data.setdefault("distro", args.DISTRO)
    if "network" in data:
        if "subnet" not in data:
            raise ValueError("'subnet' is required for 'external' networks")
    else:
        data.setdefault("subnet", "192.168.159.0/24")
    data.setdefault("container_fqdn", False)

    # generate configuration
    compose_config = gen_compose_data(data)
    inventory_config = gen_inventory_data(data)

    # save configuration
    os.makedirs(base_dir, exist_ok=True)

    gen_external_node_configuration(data, base_dir, compose_config)

    save_data(yaml, base_dir, "compose.yml", compose_config)
    save_data(yaml, base_dir, "inventory.yml", inventory_config)

    save_containers_data(data, base_dir, args)
    save_ansible_data(data, base_dir, args)
    gen_optional_files(data, base_dir, yaml)

    # process user extra_data
    if "extra_data" in data:
        cwd = os.getcwd()
        for helper in data["extra_data"]:
            copy_helper_files(base_dir, helper, source=cwd)


def main():
    """Trap execution exceptions."""
    debug = "--debug" in sys.argv
    try:
        generate_ipalab_configuration()
    except (ValueError, FileNotFoundError) as err:  # pragma: no cover
        if debug:
            raise err from None
        return die(str(err))
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
