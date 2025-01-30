"""Helper functions to generate an Ansible YAML inventory file."""

from ipalab_config.utils import die, get_hostname, ensure_fqdn


def get_node_name(name, deployment):
    """Return the proper name to use for the node."""
    if deployment["container_fqdn"]:
        return ensure_fqdn(name, deployment["domain"])
    return name


def get_server_inventory(config, default_config, deployment):
    """Get inventory configuration for the ipaserver"""
    cap_opts = {
        "DNS": {
            "ipaserver_setup_dns": True,
            "ipaserver_auto_forwarders": True,
            "ipaserver_forward_policy": "first",
            "ipaserver_no_dnssec_validation": True,
            "ipaserver_auto_reverse": True,
        },
        "KRA": {
            "ipaserver_setup_kra": True,
        },
        "AD": {"ipaserver_setup_adtrust": True},
        "RSN": {"ipaserver_random_serial_numbers": True},
    }

    name = get_node_name(config["name"], deployment)
    hostname = get_hostname(config, name, deployment["domain"])
    options = {"ipaserver_hostname": hostname, **default_config}
    for cap in config.get("capabilities", []):
        options.update(cap_opts.get(cap, {}))
    options.update(
        {
            "ipaclient_no_ntp": False,
            "ipaserver_setup_firewalld": False,
            "ipaserver_no_host_dns": True,
        }
    )
    options.update(dict(config.get("vars", {})))
    return {name: options}


def get_replicas_inventory(replicas_config, default_config, deployment):
    """Get inventory configuration for the ipaserver"""
    if not replicas_config:
        return {}
    result = {}
    cap_opts = {
        "DNS": {
            "ipareplica_setup_dns": True,
            "ipareplica_auto_forwarders": True,
            "ipareplica_forward_policy": "first",
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
        "ipareplica_setup_firewalld": False,
        "ipareplica_no_host_dns": True,
        **default_config,
    }
    server = deployment.get("server")
    if server:
        common["ipareplica_servers"] = server["ipaserver_hostname"]
    replicas = result.setdefault("hosts", {})
    domain = deployment["domain"]
    for replica in replicas_config:
        name = get_node_name(replica["name"], deployment)
        hostname = get_hostname(replica, name, domain)
        options = {"ipareplica_hostname": hostname, **common}
        for cap in replica.get("capabilities", []):
            options.update(cap_opts.get(cap, {}))
        options.update(dict(replica.get("vars", {})))
        replicas[name] = options
    return result


def get_clients_inventory(config, default_config, deployment):
    """Get inventory configuration for the ipaserver"""
    result = {}
    common = {**default_config}
    server = deployment.get("server")
    if server:
        common["ipaadmin_password"] = server["ipaadmin_password"]
        common["ipaclient_servers"] = server["ipaserver_hostname"]
    if isinstance(config, dict):
        client_list = config.get("hosts", [])
        common.update(config.get("vars", {}))
    else:
        client_list = config
    if not client_list:
        return {}
    clients = result.setdefault("hosts", {})
    for client in client_list or []:
        name = get_node_name(client["name"], deployment)
        hostname = get_hostname(client, name, deployment["domain"])
        clients[name] = {"ipaclient_hostname": hostname, **common}
        clients[name].update(dict(client.get("vars", {})))
    return result


def gen_inventory_external_nodes(lab_config, lab):
    """Create inventory configuration for IPA external nodes."""
    external = lab_config.get("external", {})
    if not external.get("hosts"):
        return
    children = lab.setdefault("children", {})
    external_inv = children.setdefault("external", {})
    if "vars" in external:
        external_inv["vars"] = external["vars"]
    groups = external_inv.setdefault("children", {})
    for node in external["hosts"]:
        group = groups.setdefault(
            f"role_{node.get("role", "none")}", {"hosts": {}}
        )
        variables = node.get("vars", {})
        group["hosts"][node["name"]] = dict(variables) if variables else None


def gen_inventory_ipa_deployments(lab_config, lab):
    """Create inventory configuration for IPA deployments."""
    lab_deployments = lab.setdefault("children", {})
    ipa_deployments = lab_config.setdefault("ipa_deployments", [])
    deployment_dns = lab_config["deployment_nameservers"]
    for deployment, nameservers in zip(ipa_deployments, deployment_dns):
        name = deployment["name"]
        domain = deployment.setdefault("domain", "ipa.local")
        deployment.setdefault("subnet", lab_config["subnet"])
        deployment.setdefault("container_fqdn", lab_config["container_fqdn"])
        config = {"children": {}}
        lab_deployments[name] = config
        default_config = {
            "ipaadmin_password": deployment.get(
                "admin_password", "SomeADMINpassword"
            ),
            "ipadm_password": deployment.get("dm_password", "SomeDMpassword"),
            "ipaserver_domain": domain,
            "ipaserver_realm": deployment.get("realm", domain).upper(),
            "ipaclient_no_ntp": True,
            **deployment.get("vars", {}),
        }
        cluster_config = deployment.get("cluster")
        if not cluster_config:  # pragma: no cover
            die(f"Cluster not defined for domain '{domain}'")
        # parse first server
        servers = cluster_config.get("servers")
        if servers:
            server = get_server_inventory(
                servers[0], default_config, deployment
            )
            config["children"]["ipaserver"] = {"hosts": server}
            deployment["server"] = next(iter(server.values()))
            if deployment["server"].get("ipaserver_setup_dns", True):
                default_config.update(
                    {
                        "ipaclient_cleanup_dns_resolver": True,
                        "ipaclient_configure_dns_resolver": True,
                        "ipaclient_dns_servers": nameservers,
                    }
                )
            # parse replicas
            replicas = get_replicas_inventory(
                servers[1:],
                default_config,
                deployment,
            )
            if replicas:
                config["children"]["ipareplicas"] = replicas
        # parse clients
        clients_config = cluster_config.get("clients")
        client_base_config = {
            key: value
            for key, value in default_config.items()
            if not any(map(key.startswith, ["ipaserver_", "ipadm_"]))
        }
        client_base_config.update({"ipaserver_domain": domain})
        clients = get_clients_inventory(
            clients_config, client_base_config, deployment
        )
        if clients:
            config["children"]["ipaclients"] = clients
    return ipa_deployments


def gen_inventory_data(lab_config):
    """Generate inventory file based on provided configuration"""
    labname = lab_config["lab_name"]
    lab = {"vars": {"ansible_connection": "podman"}}
    gen_inventory_external_nodes(lab_config, lab)
    gen_inventory_ipa_deployments(lab_config, lab)
    node_names = list(lab_config["ipa_deployments"])
    node_names.extend(list(lab["children"].get("external", {}).keys()))
    if any(
        labname == deployment["name"]
        for deployment in lab_config["ipa_deployments"]
    ):
        raise ValueError(f"Deployment name must be unique: {labname}")

    return {labname.replace("-", "_"): lab}
