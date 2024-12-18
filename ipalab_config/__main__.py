"""Generate compose and inventory configuration for a FreeIPA cluster."""

import argparse
import os
import shutil
import importlib.resources

from ruamel.yaml import YAML

from ipalab_config import __version__
from ipalab_config.utils import die
from ipalab_config.compose import gen_compose_data
from ipalab_config.inventory import gen_inventory_data


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

    return opt_parser.parse_args()


def copy_helper_files(base_dir, directory):
    """Copy directory helper files to target directory"""
    target_dir = os.path.join(base_dir, directory)
    os.makedirs(target_dir, exist_ok=True)
    origin = os.path.join(
        importlib.resources.files("ipalab_config"), "data", directory
    )
    shutil.copytree(origin, target_dir, dirs_exist_ok=True)


def save_data(yaml, base_dir, filename, yamldata):
    """Save YAML data as a YAML file."""
    os.makedirs(base_dir, exist_ok=True)
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, filename), "w") as out:
        yaml.dump(yamldata, out)


def copy_extra_files(files, target_dir):
    """Copy files to the target directory."""
    for source in files:
        filename = os.path.basename(source)
        shutil.copyfile(source, os.path.join(target_dir, filename))


def generate_ipalab_configuration():
    """Generate compose and inventory."""
    args = parse_arguments()
    yaml = YAML()

    try:
        # pylint: disable=unspecified-encoding
        with open(args.CONFIG, "r") as config_file:
            data = yaml.load(config_file.read())
    except FileNotFoundError as fnfe:
        die(str(fnfe))

    labname = data.setdefault("lab_name", "ipa-lab")
    base_dir = args.OUTPUT or labname

    # set default values
    data.setdefault("subnet", "192.168.159.0/24")
    data.setdefault("container_fqdn", False)

    compose_config = gen_compose_data(data)
    save_data(yaml, base_dir, "compose.yml", compose_config)

    inventory_config = gen_inventory_data(data)
    save_data(yaml, base_dir, "inventory.yml", inventory_config)

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

    for helper in ["containerfiles", "playbooks"]:
        copy_helper_files(base_dir, helper)

    # Copy containerfiles to result directory
    copy_extra_files(
        data.get("containerfiles", []) + args.RECIPES,
        os.path.join(base_dir, "containerfiles"),
    )

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


def main():
    """Trap execution exceptions."""
    try:
        generate_ipalab_configuration()
    except FileNotFoundError as fnfe:
        die(str(fnfe))


if __name__ == "__main__":
    main()
