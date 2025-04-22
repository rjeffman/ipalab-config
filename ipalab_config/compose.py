"""Helper funcitions to generate a podman compose file."""

from collections import namedtuple

from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from ruamel.yaml.comments import CommentedMap

from ipalab_config.utils import (
    die,
    get_hostname,
    is_ip_address,
    ensure_fqdn,
    get_ip_address_generator,
    import_external_role_module,
)


IP_GENERATOR = get_ip_address_generator()

# Use namedtuple as a class
Network = namedtuple("Network", ["domain", "name", "dns"])


def get_effective_nameserver(nameserver, domain):
    """Return the effective nameserver."""
    if nameserver and not (is_ip_address(nameserver) or "{" in nameserver):
        return f"{{{ensure_fqdn(nameserver, domain)}}}"
    return nameserver


def get_node_base_config(  # pylint: disable=R0913,R0917
    name, hostname, networkname, ipaddr, distro, tag=None
):
    """Returns the basic node configuration."""
    # fmt: off
    result = CommentedMap({
        "container_name": name,
        # Use DoubleQuotedScalarString as 'no' without quentos may be
        # interpreted as boolean False by PyYAML loaders.
        "restart": DoubleQuotedScalarString("no"),
        "cap_add": ["SYS_ADMIN", "DAC_READ_SEARCH"],
        "security_opt": ["label=disable"],
        "hostname": hostname,
        "networks": {networkname: {"ipv4_address": str(ipaddr)}},
        "image": f"localhost/{distro}:{'latest' if tag is None else tag}",
        "build": {
            "context": "containerfiles",
            "dockerfile": f"{distro}",
        },
    })
    # fmt: on
    supported_distros = {"fedora", "centos", "external-nodes", "ubuntu"}
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


def get_container_name(name, domain, container_fqdn):
    """Ensure proper creation of container name."""
    if container_fqdn:
        name = ensure_fqdn(name, domain)
    return name


def get_compose_config(containers, ips=IP_GENERATOR, **kwargs):
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
    for container in containers:
        name = get_container_name(
            container["name"], network.domain, container_fqdn
        )
        node_distro = container.get("distro", distro)
        node_tag = container.get("tag", tag)
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

        volumes = container.get("volumes", [])
        if not isinstance(volumes, (list, tuple)):
            volumes = [volumes]
        if mount_varlog and not container.get("nolog", False):
            volumes.extend([f"${{PWD}}/logs/{name}:/var/log:rw"])
        if volumes:
            config.update({"volumes": volumes})

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
        config = {
            "network": Network(
                domain,
                networkname,
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
                servers, ip_generator, **config
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
            print(f"Warning: No servers defined for domain '{domain}'")
            lab_config["deployment_nameservers"].append(None)
        # Get clients configuration
        clients = cluster_config.get("clients")
        ips, clients_cfg = get_compose_config(clients, ip_generator, **config)
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
    nodes, services = get_compose_config(ext_nodes, ip_generator, **node_config)
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
        if not role:
            continue
        try:
            module = import_external_role_module(role)
        except ImportError:
            raise RuntimeError(f"Invalid external role: {role}") from None
        service = services[node["name"]]
        service.update(getattr(module, "base_config", {}))
        volumes = service.pop("volumes", None)
        # Merge volumes with user configuration
        if volumes:
            uservol = service.get("volumes", [])
            uservol.extend(volumes)
            service["volumes"] = uservol
        service["external_node"] = node
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
