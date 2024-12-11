"""Generate compose and inventory configuration for a FreeIPA cluster."""

import argparse
import os
import shutil
import importlib.resources

from random import randint

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
    opt_parser.add_argument(
        "-o",
        "--output",
        dest="OUTPUT",
        metavar="OUTPUT",
        default=None,
        help="Output directory",
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

    labname = data.get("lab_name", "ipa-lab")

    base_dir = args.OUTPUT or labname
    for helper in ["containerfiles", "playbooks"]:
        copy_helper_files(base_dir, helper)

    subnet = f"192.168.{randint(0, 255)}"
    compose_config = gen_compose_data(data, subnet)
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, f"compose.yml"), "w") as out:
        yaml.dump(compose_config, out)

    inventory_config = gen_inventory_data(data, subnet)
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, f"inventory.yml"), "w") as out:
        yaml.dump(inventory_config, out)


def main():
    """Trap execution exceptions."""
    try:
        generate_ipalab_configuration()
    except FileNotFoundError as fnfe:
        die(str(fnfe))


if __name__ == "__main__":
    main()
