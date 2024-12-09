"""Generate compose and inventory configuration for a FreeIPA cluster."""

import argparse
import os
import sys
import shutil
import importlib.resources

from random import randint

from ruamel.yaml import YAML


__version__ = "0.1.0"


def die(msg, err=1):
    """Display message to stderr stream and exit program with error."""
    print(msg, file=sys.stderr)
    sys.exit(err)


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


def get_compose_config(containers, domain, networkname, subnet, ips):
    """Create config for all containers in the list."""
    result = {}
    if isinstance(containers, dict):
        containers = containers.get("hosts", [])
    if not containers:
        return {}
    for container, ipaddr in zip(containers, ips):
        name = container["name"]
        distro = container.get("distro", "fedora-latest")
        config = {
            "container_name": name,
            "systemd": True,
            "no_hosts": True,
            "restart": "never",
            "cap_add": ["SYS_ADMIN"],
            "security_opt": ["label:disable"],
            "hostname": container.get("hostname", f"{name}.{domain}"),
            "networks": {networkname: {"ipv4_address": f"{subnet}.{ipaddr}"}},
            "image": f"localhost/{distro}",
            "build": {
                "context": "containerfiles",
                "dockerfile": f"{distro}",
            },
        }
        result[name] = config
    return result


def compose_servers(servers, domain, networkname, subnet):
    """Generate service compose configuration for IPA servers."""
    if not servers:
        print(f"Warning: No servers defined for domain '{domain}'")
        return {}
    return get_compose_config(
        servers, domain, networkname, subnet, range(10, 10 + len(servers))
    )


def compose_clients(clients, domain, networkname, subnet):
    """Generate service compose configuration for IPA clents."""
    return get_compose_config(
        clients, domain, networkname, subnet, range(250, 10, -1)
    )


def gen_compose_file(lab_config, subnet):
    """Generate podamn compose file based on provided configuration."""
    labname = lab_config.get("lab_name", "ipa-lab")
    config = {"name": labname}
    networkname = f"ipanet-{labname}"
    config["networks"] = {
        networkname: {
            "driver": "bridge",
            "ipam": {
                "config": [
                    {
                        "subnet": f"{subnet}.0/24",
                        "gateway": f"{subnet}.1",
                    }
                ]
            },
        }
    }
    services = config.setdefault("services", {})

    ipa_deployments = lab_config.get("ipa_deployments")
    for deployment in ipa_deployments:
        domain = deployment.get("domain", "ipa.test")
        cluster_config = deployment.get("cluster")
        if not cluster_config:
            die(f"Cluster not defined for domain '{domain}'")
        servers = cluster_config.get("servers")
        services.update(
            compose_servers(
                servers,
                domain,
                networkname,
                subnet,
            )
        )
        clients = cluster_config.get("clients")
        services.update(
            compose_clients(
                clients,
                domain,
                networkname,
                subnet,
            )
        )
        if not servers and not clients:
            die("At least one server or client must be defined for {domain}.")

    return config


def get_server_inventory(config, domain, subnet):
    """Get inventory configuration for the ipaserver"""
    cap_opts = {
        "DNS": {
            "ipaserver_setup_dns": True,
            "ipaserver_auto_forwarders": False,
            "ipaserver_forward_policy": "first",
            "ipaserver_forwarders": [f"{subnet}.1"],
            "ipaserver_no_dnssec_validation": True,
            "ipaserver_auto_reverse": True,
        },
        "KRA": {
            "ipaserver_setup_dns": True,
        },
        "AD": {"ipaserver_setup_adtrust": True},
    }

    name = config["name"]
    hostname = config.get("hostname", f"{name}.{domain}")
    options = {"ipaserver_hostname": hostname}
    for cap in config.get("capabilities", []):
        options.update(cap_opts.get(cap, {}))
    options.update(
        {
            "ipaclient_no_ntp": False,
            "ipaserver_setup_firewalld": False,
            "ipaserver_no_host_dns": True,
        }
    )
    options.update(config.get("vars", {}))
    return {name: options}


def gen_dns_resolver_fix_vars(subnet):
    return {
        "ipaclient_cleanup_dns_resolver": True,
        "ipaclient_configure_dns_resolver": True,
        "ipaclient_dns_servers": [f"{subnet}.10"],
    }


def get_replicas_inventory(config, domain, subnet, server):
    """Get inventory configuration for the ipaserver"""
    result = {}
    if not config:
        return {}
    cap_opts = {
        "DNS": {
            "ipareplica_setup_dns": True,
            "ipareplica_auto_forwarders": False,
            "ipareplica_forward_policy": "first",
            "ipareplica_forwarders": [f"{subnet}.1"],
            "ipareplica_no_dnssec_validation": True,
            "ipareplica_auto_reverse": True,
        },
        "KRA": {
            "ipareplica_setup_dns": True,
        },
        "AD": {"ipareplica_setup_adtrust": True},
        "CA": {"ipareplica_setup_ca": True},
        "HIDDEN": {"ipareplica_hidden_replica": True},
    }

    # commom options
    common = {
        "ipaclient_no_ntp": False,
        "ipareplica_setup_firewalld": False,
        "ipareplica_no_host_dns": True,
    }
    if server:
        common["ipareplica_servers"] = server["ipaserver_hostname"]
        if server.get("ipaserver_setup_dns"):
            common.update(
                {
                    **gen_dns_resolver_fix_vars(subnet),
                }
            )
    result["vars"] = common
    replicas = result.setdefault("hosts", {})
    for replica in config:
        name = replica["name"]
        hostname = replica.get("hostname", f"{name}.{domain}")
        options = {"ipareplica_hostname": hostname}
        for cap in replica.get("capabilities", []):
            options.update(cap_opts.get(cap, {}))
        options.update(replica.get("vars", {}))
        replicas[name] = options
    return result


def get_clients_inventory(config, domain, subnet, server):
    """Get inventory configuration for the ipaserver"""
    result = {}
    common = {}
    if server:
        common["ipaclient_servers"] = server["ipaserver_hostname"]
        if server.get("ipaserver_setup_dns"):
            common.update(gen_dns_resolver_fix_vars(subnet))
    if common:
        result["vars"] = common
    if isinstance(config, dict):
        client_list = config.get("hosts", [])
        host_vars = config.get("vars", {})
        if host_vars:
            if "vars" not in result:
                result["vars"] = host_vars
            else:
                result["vars"].update(host_vars)
    else:
        client_list = config
    clients = result.setdefault("hosts", {})
    for client in client_list:
        name = client["name"]
        hostname = client.get("hostname", f"{name}.{domain}")
        clients[name] = {"ipaclient_hostname": hostname}
        clients[name].update(client.get("vars", {}))
    return result


def gen_inventory_file(lab_config, subnet):
    """Generate inventory file based on provided configuration"""
    labname = lab_config.get("lab_name", "ipa-lab")
    lab = {}
    ipa_deployments = lab_config.get("ipa_deployments")
    for deployment in ipa_deployments:
        name = deployment["name"].replace(".", "_")
        domain = deployment["domain"]
        config = {
            "vars": {
                "ansible_connection": "podman",
                "ipaadmin_password": lab_config.get(
                    "admin_password", "SomeADMINpassword"
                ),
                "ipadm_password": lab_config.get(
                    "dm_password", "SomeDMpassword"
                ),
                "ipaserver_domain": domain,
                "ipaserver_realm": deployment.get("realm", domain).upper(),
                "ipaclient_no_ntp": True,
                **deployment.get("vars", {}),
            },
            "children": {},
        }
        lab[name] = config
        cluster_config = deployment.get("cluster")
        if not cluster_config:
            die(f"Cluster not defined for domain '{domain}'")
        # parse first server
        servers = cluster_config.get("servers")
        if not servers:
            server_data = {}
        else:
            server = get_server_inventory(servers[0], domain, subnet)
            config["children"]["ipaserver"] = {"hosts": server}
            server_data = next(iter(server.values()))
            # parse replicas
            replicas = get_replicas_inventory(
                servers[1:], domain, subnet, server_data
            )
            if replicas:
                config["children"]["ipareplicas"] = replicas
        # parse clients
        clients_config = cluster_config.get("clients")
        clients = get_clients_inventory(
            clients_config, domain, subnet, server_data
        )
        if clients:
            config["children"]["ipaclients"] = clients

    return {labname.replace("-", "_"): {"children": lab}}


def copy_helper_files(base_dir, directory):
    """Copy directory helper files to target directory"""
    target_dir = os.path.join(base_dir, directory)
    os.makedirs(target_dir, exist_ok=True)
    origin = os.path.join(
        importlib.resources.files("ipalab_config"), "data", directory
    )
    shutil.copytree(origin, target_dir, dirs_exist_ok=True)


def main():
    """Program entry-point."""

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
    compose_config = gen_compose_file(data, subnet)
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, f"compose.yml"), "w") as out:
        yaml.dump(compose_config, out)

    inventory_config = gen_inventory_file(data, subnet)
    # pylint: disable=unspecified-encoding
    with open(os.path.join(base_dir, f"inventory.yml"), "w") as out:
        yaml.dump(inventory_config, out)


if __name__ == "__main__":
    main()
