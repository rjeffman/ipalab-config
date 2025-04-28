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
    options = (
        {}
        if config.get("no_limit_uid")
        else {
            "ipaserver_idstart": 60001,
            "ipaserver_idmax": 62000,
            "ipaserver_rid_base": 63000,
            "ipaserver_secondary_rid_base": 65000,
        }
    )
    options.update({"ipaserver_hostname": hostname, **default_config})
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
    replicas = {}
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
    domain = deployment["domain"]
    for replica in replicas_config:
        name = get_node_name(replica["name"], deployment)
        hostname = get_hostname(replica, name, domain)
        options = {"ipareplica_hostname": hostname, **common}
        for cap in replica.get("capabilities", []):
            options.update(cap_opts.get(cap, {}))
        options.update(dict(replica.get("vars", {})))
        replicas[name] = options
    return replicas


def get_clients_inventory(config, default_config, deployment):
    """Get inventory configuration for the ipaserver"""
    clients = {}
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
    for client in client_list or []:
        name = get_node_name(client["name"], deployment)
        hostname = get_hostname(client, name, deployment["domain"])
        clients[name] = {"ipaclient_hostname": hostname, **common}
        clients[name].update(dict(client.get("vars", {})))
    return clients


def gen_inventory_external_nodes(lab_config, lab):
    """Create inventory configuration for IPA external nodes."""
    external = lab_config.get("external", {})
    if not external.get("hosts"):
        return
    hosts = lab.setdefault("hosts", {})
    external_inv = (
        lab.setdefault("children", {})
        .setdefault("external", {})
        .setdefault("hosts", {})
    )
    if "vars" in external:
        external_inv["vars"] = external["vars"]
    for node in external["hosts"]:
        group = lab.setdefault("children", {}).setdefault(
            f"role_{node.get("role", "none")}", {"hosts": {}}
        )
        variables = node.get("vars", {})
        hosts[node["name"]] = dict(variables) if variables else None
        group["hosts"].update({node["name"]: None})
        external_inv.update({node["name"]: None})


def gen_inventory_ipa_deployments(lab_config, lab):
    """Create inventory configuration for IPA deployments."""

    def add_hosts_to_inventory(lab_name, lab, item, data):
        # add to host list
        hosts = lab.setdefault("hosts", {})
        hosts.update(data)
        # groups
        lab_child = lab.setdefault("children", {})
        # add to group list
        group = lab_child.setdefault(item, {}).setdefault("hosts", {})
        group.update({item: None for item in data})
        # fmt: off
        # add to deployment list
        deployment_inv = (
            lab_child.setdefault(lab_name, {}).setdefault("hosts", {})
        )
        # fmt: on
        deployment_inv.update({item: None for item in data})

    ipa_deployments = lab_config.setdefault("ipa_deployments", [])
    deployment_dns = lab_config["deployment_nameservers"]
    if len(ipa_deployments) > 1 and not lab_config["container_fqdn"]:
        raise ValueError(
            "With multiple IPA deployments, "
            "'container_fqdn' must be set to 'true'."
        )
    for deployment, nameservers in zip(ipa_deployments, deployment_dns):
        name = deployment["name"]
        # process deployment
        domain = deployment.setdefault("domain", lab_config.get("domain"))
        deployment.setdefault("subnet", lab_config["subnet"])
        deployment.setdefault("container_fqdn", lab_config["container_fqdn"])
        default_config = {
            "ipaadmin_password": deployment.get(
                "admin_password", "SomeADMINpassword"
            ),
            "ipadm_password": deployment.get("dm_password", "SomeDMpassword"),
            "ipaserver_realm": deployment.get("realm", domain).upper(),
            "ipaclient_no_ntp": True,
            **deployment.get("vars", {}),
        }
        if domain and "ipaserver_domain" not in default_config:
            default_config["ipaserver_domain"] = domain
        cluster_config = deployment.get("cluster")
        if not cluster_config:  # pragma: no cover
            die(f"Cluster not defined for domain '{domain}'")
        # parse first server
        servers = cluster_config.get("servers")
        if servers:
            server = get_server_inventory(
                servers[0], default_config, deployment
            )
            add_hosts_to_inventory(name, lab, "ipaserver", server)
            # set deployment first server
            deployment["server"] = next(iter(server.values()))
            if deployment["server"].get("ipaserver_setup_dns", False):
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
                add_hosts_to_inventory(name, lab, "ipareplicas", replicas)
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
            add_hosts_to_inventory(name, lab, "ipaclients", clients)
        # add deployment to inventory
        lab["children"].setdefault("ipa_deployments", {"children": {}})
        lab["children"]["ipa_deployments"]["children"][name] = None
    return ipa_deployments


def gen_inventory_data(lab_config):
    """Generate inventory file based on provided configuration"""
    labname = lab_config["lab_name"]
    lab = {"vars": {"ansible_connection": "podman"}}
    gen_inventory_external_nodes(lab_config, lab)
    gen_inventory_ipa_deployments(lab_config, lab)
    node_names = list(lab_config["ipa_deployments"])
    node_names.extend(list(lab.get("external", {}).keys()))
    if any(
        labname == deployment["name"]
        for deployment in lab_config["ipa_deployments"]
    ):
        raise ValueError(f"Deployment name must be unique: {labname}")

    return {labname.replace("-", "_"): lab}
