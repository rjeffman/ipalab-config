"""Helper functions to generate a podman compose file."""

from collections import namedtuple

from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.comments import CommentedMap

from ipalab_config.logger import logger
from ipalab_config.utils import (
    die,
    get_hostname,
    is_ip_address,
    ensure_fqdn,
    get_ip_address_generator,
    clear_ip_generators,
    import_external_role_module,
)


# Use namedtuple as a class
Network = namedtuple("Network", ["domain", "name", "dns"])


def get_effective_nameserver(nameserver, domain):
    """Return the effective nameserver."""
    if nameserver and not (is_ip_address(nameserver) or "{" in nameserver):
        return f"{{{ensure_fqdn(nameserver, domain)}}}"
    return nameserver


def get_node_base_config(  # pylint: disable=R0913,R0917
    name, hostname, networkname, ipaddr, distro=None, tag=None, image=None
):
    """Returns the basic node configuration."""
    node_image = {}
    if distro is None and image is None:
        distro = "fedora"
    if distro:
        node_image = {
            "image": f"localhost/{distro}:{'latest' if tag is None else tag}",
            "build": {
                "context": "containerfiles",
                "dockerfile": f"{distro}",
            },
        }
    if image:
        node_image = {"image": image}

    # fmt: off
    result = CommentedMap({
        "container_name": name,
        # Use DoubleQuotedScalarString as 'no' without quotes may be
        # interpreted as boolean False by PyYAML loaders.
        "restart": DoubleQuotedScalarString("no"),
        "cap_add": ["SYS_ADMIN", "DAC_READ_SEARCH"],
        "security_opt": ["label=disable"],
        "hostname": hostname,
        "extra_hosts": [f"{hostname}:{str(ipaddr)}"],
        "networks": {networkname: {"ipv4_address": str(ipaddr)}},
        **node_image
    })
    # fmt: on
    supported_distros = {"fedora", "centos", "external-nodes", "ubuntu"}
    if "build" in result:
        if tag is not None and distro in supported_distros:
            args = {"distro_image": distro, "distro_tag": tag}
            result["build"]["args"] = args
        else:
            # If no tag is given, and distro is one of the ipalab-config
            # provided ones, add a commented our "args" option to "build".
            if distro in supported_distros:
                result.yaml_set_comment_before_after_key(
                    "build",
                    after=(
                        "You may set the desired distro/version setting:\n"
                        f"args: {{distro_image: {distro}, distro_tag: latest}}"
                    ),
                    after_indent=6,
                )
    return result


def get_container_name(container, domain, container_fqdn):
    """Ensure proper creation of container name."""
    name = container["name"]
    if container_fqdn:
        if container.get("hostname"):
            name = ensure_fqdn(container["hostname"], domain)
        else:
            name = ensure_fqdn(name, domain)
    return name


def get_compose_config(containers, subnet=None, **kwargs):
    """Create config for all containers in the list."""

    def node_dns_key(hostname):
        return hostname.replace(".", "_")

    if isinstance(containers, dict):
        containers = containers.get("hosts", [])
    if not containers:
        return {}, {}
    result = {}
    nodes = {}
    network = kwargs.get("network")
    if network is None:
        raise RuntimeError("Node network not defined.")
    container_fqdn = kwargs.get("container_fqdn", False)
    distro = kwargs.get("distro", "fedora")
    tag = kwargs.get("tag")
    mount_varlog = kwargs.get("mount_varlog", False)
    # Get the IP generator for this subnet (cached by subnet string)
    ips = get_ip_address_generator(subnet)
    for container in containers:
        name = get_container_name(container, network.domain, container_fqdn)
        node_distro = container.get("distro", distro)
        node_tag = container.get("tag", tag)
        node_image = container.get("image")
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
            node_tag,
            node_image,
        )
        if "memory" in container:
            config.update(
                {"mem_limit": container["memory"].lower(), "memory_swap": -1}
            )
        if container.get("publish_ports"):
            config["ports"] = container["publish_ports"]
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

        volumes = container.get("volumes", [])
        if not isinstance(volumes, (list, tuple)):
            volumes = [volumes]
        if mount_varlog and not container.get("nolog", False):
            volumes.extend([f"${{PWD}}/logs/{name}:/var/log:rw"])
        if volumes:
            config.update({"volumes": volumes})

        result[name] = config
    return nodes, result


def get_network_config(  # pylint: disable=R0912
    lab_config, network_def=None, network_suffix=None
):
    """Generate the compose "networks" configuration.

    Args:
        lab_config: The lab configuration dictionary
        network_def: Optional network definition for per-deployment
        network_suffix: Suffix for network name (default: lab name)

    Returns:
        tuple: (networkname, subnet, network_config_dict)
    """
    subnet = lab_config.get("subnet")
    # Use provided network_def or fall back to global network
    network = network_def or (lab_config.get("network") or {})
    # Use provided suffix or fall back to lab name
    if network_suffix is None:
        network_suffix = lab_config["lab_name"]

    if isinstance(network, str):
        networkname = network
        config = {networkname: {"external": True}}
    else:
        # For per-deployment networks, use unique name if not set
        if network_def is not None and "name" not in network:
            # Use suffix as part of networkname for uniqueness
            networkname = f"ipanet-{network_suffix}"
        else:
            networkname = network.get("name", "ipanet")
        name = network.get("name", f"ipanet-{network_suffix}")
        subnet = network.get("subnet", subnet or "192.168.159.0/24")
        config = {
            networkname: {
                "name": name,
                "driver": network.get("driver", "bridge"),
                "ipam": {"config": [{"subnet": subnet}]},
            }
        }
        no_dns = network.get("no_dns", False)
        if network.get("external"):
            config[networkname]["external"] = True
        if no_dns or "dns" in network:
            logger.warning("DNS options require 'podman-compose > 1.3.0'")
        if no_dns:
            config[networkname]["x-podman.disable_dns"] = True
        if "dns" in network:
            dns = network["dns"]
            if not dns:
                raise ValueError("'network.dns' must not be empty")
            if not isinstance(dns, (str, list)):
                raise ValueError("'network.dns' must be a string or a list")
            config[networkname]["x-podman.dns"] = dns
    # Ensure subnet is correctly set
    if config[networkname].get("external", False) and subnet is None:
        raise ValueError("'subnet' is required for 'external' networks")
    # # Only set global subnet if we're processing the global network
    if network_def is None:
        lab_config.setdefault("subnet", subnet)
    return networkname, subnet, config


def get_ipa_deployments_configuration(
    lab_config, global_networkname, global_subnet, networks_config
):
    """Generate compose configuration for all IPA deployments.

    Args:
        lab_config: The lab configuration dictionary
        global_networkname: The global network name to use as fallback
        global_subnet: Subnet CIDR for global network
        networks_config: Dictionary to accumulate network configs

    Returns:
        dict: Services configuration for all deployments
    """
    lab_config.setdefault("deployment_nameservers", [])
    labdns = lab_config.get("dns")
    labdomain = lab_config.get("domain")
    services = {}
    for deployment in lab_config.setdefault("ipa_deployments", []):
        domain = deployment.get("domain", labdomain)
        dns = deployment.get("dns", labdns)
        if dns and not is_ip_address(dns):
            # pylint: disable=consider-using-f-string
            dns = "{{{0}}}".format(ensure_fqdn(dns, domain))

        # Check if deployment has its own network configuration
        deployment_network = deployment.get("network")
        if deployment_network is not None:
            # Create a separate network for this deployment
            deployment_name = deployment.get("name", domain.split(".")[0])
            net_name, net_subnet, net_config = get_network_config(
                lab_config, deployment_network, deployment_name
            )
            # Add to networks configuration
            networks_config.update(net_config)
            # Use deployment-specific network and subnet
            current_networkname = net_name
            current_subnet = net_subnet
        else:
            # Use global network
            current_networkname = global_networkname
            current_subnet = global_subnet

        config = {
            "network": Network(
                domain,
                current_networkname,
                get_effective_nameserver(dns, domain),
            ),
            "container_fqdn": lab_config["container_fqdn"],
            "distro": deployment.get("distro", lab_config["distro"]),
            "tag": deployment.get("tag", lab_config.get("tag")),
            "mount_varlog": lab_config.get("mount_varlog", False),
        }
        cluster_config = deployment.get("cluster")
        if not cluster_config:
            die(f"Cluster not defined for domain '{domain}'")
        nodes = {}
        # Get servers configurations
        servers = cluster_config.get("servers")
        if servers:
            ips, servers_cfg = get_compose_config(
                servers, current_subnet, **config
            )
            deployment_dns = [
                "{{{0}}}".format(  # pylint: disable=consider-using-f-string
                    ensure_fqdn(host["name"], domain)
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
            logger.warning(
                "No servers defined for domain '%(domain)s'",
                domain=domain,
            )
            lab_config["deployment_nameservers"].append(None)
        # Get clients configuration
        clients = cluster_config.get("clients")
        ips, clients_cfg = get_compose_config(clients, current_subnet, **config)
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


def get_external_hosts_configuration(lab_config, networkname, subnet):
    """Generate configuration for hosts external to IPA deployments."""
    external = lab_config.get("external", {})
    services = {}
    node_config = {
        "network": Network(
            external.get("domain", lab_config.get("domain", "ipalab.local")),
            networkname,
            get_effective_nameserver(lab_config.get("dns", ""), ""),
        ),
        "container_fqdn": lab_config["container_fqdn"],
        "distro": "external-nodes",
        "mount_varlog": lab_config["mount_varlog"],
    }
    ext_nodes = external.get("hosts", [])
    nodes, services = get_compose_config(ext_nodes, subnet, **node_config)
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
            # Use first nameserver as lab nameserver
            break

    # Udate external nodes
    for node in ext_nodes:
        role = node.get("role")

        def service_from_node(services, node):
            if node["name"] in services:
                return services[node["name"]]
            if node.get("hostname") in services:
                return services[node.get("hostname")]
            return None

        service = service_from_node(services, node)
        if role:
            # Use defaults for choosen role
            try:
                module = import_external_role_module(role)
            except ImportError:
                raise RuntimeError(f"Invalid external role: {role}") from None
            service.update(getattr(module, "base_config", {}))
        # Use provided node image
        if node.get("image"):
            service.pop("distro", None)
            service["image"] = node.get("image")
        # Merge volumes with user configuration
        volumes = service.pop("volumes", None)
        if volumes:
            uservol = service.get("volumes", [])
            uservol.extend(volumes)
            service["volumes"] = uservol
        # save node original configuration
        service["external_node"] = node
        # setup node DNS
        if dns:
            service["dns"] = dns

    return services


def gen_compose_data(lab_config):
    """Generate podamn compose file based on provided configuration."""
    # Clear IP generator cache for fresh start
    clear_ip_generators()

    config = {"name": lab_config["lab_name"]}
    config.setdefault("services", {})

    # Always get global network config to set lab_config["subnet"]
    # This is needed by inventory generation and other components
    networkname, subnet, networks_config = get_network_config(lab_config)

    # Check if global network is actually used
    has_external = bool(lab_config.get("external", {}).get("hosts"))
    deployments = lab_config.get("ipa_deployments", [])
    needs_global = has_external or any("network" not in d for d in deployments)

    # Only add global network to compose if it's used
    config["networks"] = networks_config if needs_global else {}

    # Add external hosts
    config["services"].update(
        get_external_hosts_configuration(lab_config, networkname, subnet)
    )
    # Add IPA deployments (may add networks to networks_config)
    config["services"].update(
        get_ipa_deployments_configuration(
            lab_config, networkname, subnet, config["networks"]
        )
    )

    return config
