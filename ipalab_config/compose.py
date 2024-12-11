"""Helper funcitions to generate a podman compose file."""

from ipalab_config.utils import die, get_hostname


# The global ip address generator.
IP_GENERATOR = iter(range(10, 255))


def get_compose_config(
    containers, domain, networkname, subnet, ips=IP_GENERATOR
):
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
            "hostname": get_hostname(container, name, domain),
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
    return get_compose_config(servers, domain, networkname, subnet)


def compose_clients(clients, domain, networkname, subnet):
    """Generate service compose configuration for IPA clents."""
    return get_compose_config(clients, domain, networkname, subnet)


def gen_compose_data(lab_config, subnet):
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
