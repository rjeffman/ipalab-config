"""Helper funcitions to generate a podman compose file."""

from collections import namedtuple

from ipalab_config.utils import (
    die,
    get_hostname,
    is_ip_address,
    ensure_fqdn,
    get_ip_address_generator,
)


IP_GENERATOR = get_ip_address_generator()


def get_effective_nameserver(nameserver, domain):
    """Return the effective nameserver."""
    if nameserver and not (is_ip_address(nameserver) or "{" in nameserver):
        return f"{{{ensure_fqdn(nameserver, domain)}}}"
    return nameserver


def get_node_base_config(name, hostname, networkname, ipaddr, node_distro):
    """Returns the basic node configuration."""
    return {
        "container_name": name,
        "systemd": True,
        "no_hosts": True,
        "restart": "never",
        "cap_add": ["SYS_ADMIN", "DAC_READ_SEARCH"],
        "security_opt": ["label:disable"],
        "hostname": hostname,
        "networks": {networkname: {"ipv4_address": str(ipaddr)}},
        "image": f"localhost/{node_distro}",
        "build": {
            "context": "containerfiles",
            "dockerfile": f"{node_distro}",
        },
    }


def get_container_name(name, domain, container_fqdn):
    """Ensure proper creation of container name."""
    if container_fqdn:
        name = ensure_fqdn(name, domain)
    return name


def get_compose_config(
    containers, network, distro, container_fqdn, ips=IP_GENERATOR
):
    """Create config for all containers in the list."""

    def node_dns_key(hostname):
        return hostname.replace(".", "_")

    if isinstance(containers, dict):
        containers = containers.get("hosts", [])
    if not containers:
        return {}, {}
    result = {}
    nodes = {}
    for container in containers:
        name = get_container_name(
            container["name"], network.domain, container_fqdn
        )
        node_distro = container.get("distro", distro)
        hostname = get_hostname(container, name, network.domain)
        ipaddr = container.get("ip_address")
        if not ipaddr:
            ipaddr = next(ips)
        nodes[node_dns_key(hostname)] = str(ipaddr)
        config = get_node_base_config(
            name,
            hostname,
            network.name,
            str(ipaddr),
            node_distro,
        )
        if "memory" in container:
            config.update(
                {"mem_limit": container["memory"].lower(), "memory_swap": -1}
            )
        # DNS
        effective_dns = get_effective_nameserver(
            container.get("dns", network.dns), network.domain
        )
        if effective_dns:
            config["dns"] = (
                effective_dns
                if is_ip_address(effective_dns)
                else node_dns_key(effective_dns)
            )
        config["dns_search"] = network.domain

        if "volumes" in container:
            config.update({"volumes": container["volumes"]})

        result[name] = config
    return nodes, result


def get_network_config(lab_config, subnet):
    """Generate the compose "networks" configuration."""
    if "network" in lab_config:
        networkname = lab_config["network"]
        config = {networkname: {"external": True}}
    else:
        networkname = "ipanet"
        config = {
            "ipanet": {
                "name": f"ipanet-{lab_config['lab_name']}",
                "driver": "bridge",
                "ipam": {"config": [{"subnet": subnet}]},
            }
        }
    return networkname, config


def get_ipa_deployments_configuration(lab_config, networkname, ip_generator):
    """Generate compose configuration for all IPA deployments."""
    Network = namedtuple("Network", ["domain", "name", "dns"])
    container_fqdn = lab_config["container_fqdn"]
    lab_config.setdefault("deployment_nameservers", [])
    labdns = lab_config.get("dns")
    labdomain = lab_config.get("domain", "ipalab.local")
    services = {}
    for deployment in lab_config.setdefault("ipa_deployments", []):
        domain = deployment.get("domain", labdomain)
        distro = deployment.get("distro", lab_config["distro"])
        dns = deployment.get("dns", labdns)
        if dns and not is_ip_address(dns):
            # pylint: disable=consider-using-f-string
            dns = "{{{0}}}".format(ensure_fqdn(dns, domain))
        network = Network(
            domain,
            networkname,
            get_effective_nameserver(dns, domain),
        )
        cluster_config = deployment.get("cluster")
        if not cluster_config:
            die(f"Cluster not defined for domain '{domain}'")
        nodes = {}
        # Get servers configurations
        servers = cluster_config.get("servers")
        if servers:
            ips, servers_cfg = get_compose_config(
                servers, network, distro, container_fqdn, ip_generator
            )
            deployment_dns = [
                "{{{0}}}".format(  # pylint: disable=consider-using-f-string
                    ensure_fqdn(host["name"], network.domain)
                )
                .replace(".", "_")
                .format(**ips)
                for host in servers
                if "DNS" in host.get("capabilities", [])
            ]
            lab_config["deployment_nameservers"].append(deployment_dns)
            services.update(servers_cfg)
            nodes.update(ips)
        else:
            print(f"Warning: No servers defined for domain '{domain}'")
            lab_config["deployment_nameservers"].append(None)
        # Get clients configuration
        clients = cluster_config.get("clients")
        ips, clients_cfg = get_compose_config(
            clients, network, distro, container_fqdn, ip_generator
        )
        services.update(clients_cfg)
        nodes.update(ips)
        # We must have at lest one node at the end.
        if not nodes:
            die("At least one server or client must be defined for {domain}.")
        # update nodes list
        lab_config.setdefault("nodes", {}).update(nodes)
        # Update 'dns' on each service
        for service in services.values():
            if "dns" in service:
                service["dns"] = service["dns"].format(**nodes)
            else:
                service.pop("dns_search", None)

    return services


def get_external_hosts_configuration(lab_config, networkname, ip_generator):
    """Generate configuration for hosts external to IPA deployments."""
    config = {
        "dns": {
            "image": "localhost/unbound",
            "build": {"context": "unbound", "dockerfile": "Containerfile"},
            "volumes": [
                "${PWD}/unbound:/etc/unbound:Z",
            ],
        },
        "addc": {
            "image": "localhost/samba-addc",
            "build": {
                "context": "containerfiles",
                "dockerfile": "external-nodes",
                "args": {"packages": "systemd"},
            },
            "command": "/usr/sbin/init",
        },
    }
    Network = namedtuple("Network", ["domain", "name", "dns"])
    container_fqdn = lab_config["container_fqdn"]
    external = lab_config.get("external", {})
    services = {}
    network = Network(
        external.get("domain", "ipalab.local"),
        networkname,
        get_effective_nameserver(lab_config.get("dns", ""), ""),
    )
    ext_nodes = external.get("hosts", [])
    nodes, services = get_compose_config(
        ext_nodes, network, "fedora-latest", container_fqdn, ip_generator
    )
    # update nodes list
    lab_config.setdefault("nodes", {}).update(nodes)

    # Handle DNS specially
    dns = None
    for node in ext_nodes:
        if node.get("role") == "dns":
            service = services[node["name"]]
            ip_address = service["networks"][networkname]["ipv4_address"]
            # Use ugly side effect
            dns = lab_config["dns"] = ip_address

    # Udate external nodes
    for node in ext_nodes:
        role = node.get("role")
        if role and role in config:
            services[node["name"]].update(config[role])
        services[node["name"]]["external_node"] = node
        if dns:
            service["dns"] = dns

    return services


def gen_compose_data(lab_config):
    """Generate podamn compose file based on provided configuration."""
    config = {"name": lab_config["lab_name"]}
    config.setdefault("services", {})

    subnet = lab_config["subnet"]
    ip_generator = get_ip_address_generator(subnet)
    networkname, config["networks"] = get_network_config(lab_config, subnet)

    # Add external hosts
    config["services"].update(
        get_external_hosts_configuration(lab_config, networkname, ip_generator)
    )
    # Add IPA deployments
    config["services"].update(
        get_ipa_deployments_configuration(lab_config, networkname, ip_generator)
    )

    return config
