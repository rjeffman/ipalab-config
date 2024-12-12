"""Helper functions to generate an Ansible YAML inventory file."""

from ipalab_config.utils import die, get_hostname


def get_server_inventory(config, domain, subnet, default_config):
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
            "ipaserver_setup_kra": True,
        },
        "AD": {"ipaserver_setup_adtrust": True},
        "RSN": {"ipaserver_random_serial_numbers": True},
    }

    name = config["name"]
    hostname = get_hostname(config, name, domain)
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
    options.update(config.get("vars", {}))
    return {name: options}


def gen_dns_resolver_fix_vars(subnet, nameserver=None):
    return {
        "ipaclient_cleanup_dns_resolver": True,
        "ipaclient_configure_dns_resolver": True,
        "ipaclient_dns_servers": [nameserver or f"{subnet}.10"],
    }


def get_replicas_inventory(
    config, domain, subnet, server, nameserver, default_config
):
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
        **default_config,
    }
    if server:
        common["ipareplica_servers"] = server["ipaserver_hostname"]
        if nameserver is None and server.get("ipaserver_setup_dns", False):
            common.update(
                {
                    **gen_dns_resolver_fix_vars(subnet, nameserver),
                }
            )
    result["vars"] = common
    replicas = result.setdefault("hosts", {})
    for replica in config:
        name = replica["name"]
        hostname = get_hostname(replica, name, domain)
        options = {"ipareplica_hostname": hostname}
        for cap in replica.get("capabilities", []):
            options.update(cap_opts.get(cap, {}))
        options.update(replica.get("vars", {}))
        replicas[name] = options
    return result


def get_clients_inventory(config, domain, subnet, server, nameserver):
    """Get inventory configuration for the ipaserver"""
    result = {}
    common = {}
    if server:
        common["ipaclient_servers"] = server["ipaserver_hostname"]
        if nameserver is None and server.get("ipaserver_setup_dns", False):
            common.update(gen_dns_resolver_fix_vars(subnet, nameserver))
    if isinstance(config, dict):
        client_list = config.get("hosts", [])
        common.update(config.get("vars", {}))
    else:
        client_list = config
    if not client_list:
        return {}
    clients = result.setdefault("hosts", {})
    for client in client_list or []:
        name = client["name"]
        hostname = get_hostname(client, name, domain)
        clients[name] = {"ipaclient_hostname": hostname, **common}
        clients[name].update(client.get("vars", {}))
    return result


def gen_inventory_data(lab_config, subnet, deployment_dns):
    """Generate inventory file based on provided configuration"""
    labname = lab_config.get("lab_name", "ipa-lab")
    lab = {"vars": {"ansible_connection": "podman"}}
    lab_deployments = lab.setdefault("children", {})
    ipa_deployments = lab_config.get("ipa_deployments")
    for deployment, nameserver in zip(ipa_deployments, deployment_dns):
        name = deployment["name"].replace(".", "_")
        domain = deployment["domain"]
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
        if not cluster_config:
            die(f"Cluster not defined for domain '{domain}'")
        # parse first server
        servers = cluster_config.get("servers")
        dns_resolver = None
        if not servers:
            server_data = {}
        else:
            server = get_server_inventory(
                servers[0], domain, subnet, default_config
            )
            config["children"]["ipaserver"] = {"hosts": server}
            server_data = next(iter(server.values()))
            # parse replicas
            replicas = get_replicas_inventory(
                servers[1:],
                domain,
                subnet,
                server_data,
                nameserver,
                default_config,
            )
            if replicas:
                config["children"]["ipareplicas"] = replicas
        # parse clients
        clients_config = cluster_config.get("clients")
        clients = get_clients_inventory(
            clients_config, domain, subnet, server_data, nameserver
        )
        if clients:
            config["children"]["ipaclients"] = clients

    return {labname.replace("-", "_"): lab}
