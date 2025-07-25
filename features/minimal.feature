Feature: Create minimal configuration
    In order to test FreeIPA using containers
    As a developer os sysadmin
    I want to provide minimal configuration in a single file and
    obtain a Podman compose file, an Ansible inventory file, and
    the minimum necessary files to create the deployment.

Scenario: Minimal single server
    Given the deployment configuration
    """
    ipa_deployments:
      - name: server_only
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
    """
      When I run ipalab-config
      Then the output directory name is "ipa-lab"
      And the ipa-lab/compose.yml file is
        """
        name: ipa-lab
        networks:
          ipanet:
            name: ipanet-ipa-lab
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server:
            container_name: server
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: server.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.2
            extra_hosts:
              - server.ipa.test:192.168.159.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            ipa_deployments: { children: { server_only: } }
            server_only: { hosts: { server: } }
            ipaserver: { hosts: { server: } }
          hosts:
            server:
              ipaserver_hostname: server.ipa.test
              ipaadmin_password: SomeADMINpassword
              ipadm_password: SomeDMpassword
              ipaserver_domain: ipa.test
              ipaserver_realm: IPA.TEST
              ipaclient_no_ntp: false
              ipaserver_setup_firewalld: false
              ipaserver_no_host_dns: true
              ipaserver_idstart: 60001
              ipaserver_idmax: 62000
              ipaserver_rid_base: 63000
              ipaserver_secondary_rid_base: 65000
        """
      And the "ipa-lab/containerfiles" directory was copied

Scenario: Minimum IPA cluster
    # Note: for a minimal cluster, it is currently required that
    # the first server provides a DNS nameserver, or that containers
    # names are FQDN.
    Given the deployment configuration
    """
    ipa_deployments:
      - name: ipa_cluster
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
              capabilities: ["DNS"]
            - name: replica
          clients:
            - name: client
    """
     When I run ipalab-config
     Then the output directory name is "ipa-lab"
      And the ipa-lab/compose.yml file is
        """
        name: ipa-lab
        networks:
          ipanet:
            name: ipanet-ipa-lab
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server:
            container_name: server
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: server.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.2
            extra_hosts:
              - server.ipa.test:192.168.159.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
          replica:
            container_name: replica
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: replica.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.3
            extra_hosts:
              - replica.ipa.test:192.168.159.3
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
          client:
            container_name: client
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: client.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.4
            extra_hosts:
              - client.ipa.test:192.168.159.4
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            ipa_deployments: { children: { ipa_cluster: } }
            ipa_cluster:
              hosts:
                server:
                replica:
                client:
            ipaserver:
              hosts: { server: }
            ipareplicas:
              hosts: { replica: }
            ipaclients:
              hosts: { client: }
          hosts:
            server:
              ipaserver_hostname: server.ipa.test
              ipaadmin_password: SomeADMINpassword
              ipadm_password: SomeDMpassword
              ipaserver_domain: ipa.test
              ipaserver_realm: IPA.TEST
              ipaclient_no_ntp: false
              ipaserver_setup_firewalld: false
              ipaserver_no_host_dns: true
              ipaserver_setup_dns: true
              ipaserver_auto_forwarders: true
              ipaserver_forward_policy: first
              ipaserver_no_dnssec_validation: true
              ipaserver_auto_reverse: true
              ipaserver_idstart: 60001
              ipaserver_idmax: 62000
              ipaserver_rid_base: 63000
              ipaserver_secondary_rid_base: 65000
            replica:
              ipareplica_hostname: replica.ipa.test
              ipaadmin_password: SomeADMINpassword
              ipadm_password: SomeDMpassword
              ipaserver_domain: ipa.test
              ipaserver_realm: IPA.TEST
              ipareplica_servers: server.ipa.test
              ipaclient_no_ntp: true
              ipareplica_setup_firewalld: false
              ipareplica_no_host_dns: true
              ipaclient_cleanup_dns_resolver: true
              ipaclient_configure_dns_resolver: true
              ipaclient_dns_servers:
                - 192.168.159.2
            client:
              ipaadmin_password: SomeADMINpassword
              ipaclient_hostname: client.ipa.test
              ipaclient_no_ntp: true
              ipaclient_servers: server.ipa.test
              ipaserver_domain: ipa.test
              ipaclient_cleanup_dns_resolver: true
              ipaclient_configure_dns_resolver: true
              ipaclient_dns_servers:
                - 192.168.159.2
        """
      And the "ipa-lab/containerfiles" directory was copied

Scenario: FQDN containers and replica capabilities
    Given the deployment configuration
    """
    container_fqdn: true
    ipa_deployments:
      - name: ipa_cluster
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
              capabilities: ["DNS"]
            - name: replica
              capabilities: ["CA", "HIDDEN"]
          clients:
            - name: client
    """
     When I run ipalab-config
     Then the output directory name is "ipa-lab"
      And the ipa-lab/compose.yml file is
        """
        name: ipa-lab
        networks:
          ipanet:
            name: ipanet-ipa-lab
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server.ipa.test:
            container_name: server.ipa.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: server.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.2
            extra_hosts:
              - server.ipa.test:192.168.159.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
          replica.ipa.test:
            container_name: replica.ipa.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: replica.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.3
            extra_hosts:
              - replica.ipa.test:192.168.159.3
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
          client.ipa.test:
            container_name: client.ipa.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: client.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.159.4
            extra_hosts:
              - client.ipa.test:192.168.159.4
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            ipa_deployments: { children: { ipa_cluster: } }
            ipa_cluster:
              hosts:
                server.ipa.test:
                replica.ipa.test:
                client.ipa.test:
            ipaserver:
              hosts: { server.ipa.test: }
            ipareplicas:
              hosts: { replica.ipa.test: }
            ipaclients:
              hosts: { client.ipa.test: }
          hosts:
            server.ipa.test:
              ipaserver_hostname: server.ipa.test
              ipaadmin_password: SomeADMINpassword
              ipadm_password: SomeDMpassword
              ipaserver_domain: ipa.test
              ipaserver_realm: IPA.TEST
              ipaclient_no_ntp: false
              ipaserver_setup_firewalld: false
              ipaserver_no_host_dns: true
              ipaserver_setup_dns: true
              ipaserver_auto_forwarders: true
              ipaserver_forward_policy: first
              ipaserver_no_dnssec_validation: true
              ipaserver_auto_reverse: true
              ipaserver_idstart: 60001
              ipaserver_idmax: 62000
              ipaserver_rid_base: 63000
              ipaserver_secondary_rid_base: 65000
            replica.ipa.test:
              ipareplica_hostname: replica.ipa.test
              ipaadmin_password: SomeADMINpassword
              ipadm_password: SomeDMpassword
              ipaserver_domain: ipa.test
              ipaserver_realm: IPA.TEST
              ipareplica_servers: server.ipa.test
              ipaclient_no_ntp: true
              ipareplica_setup_firewalld: false
              ipareplica_no_host_dns: true
              ipaclient_cleanup_dns_resolver: true
              ipaclient_configure_dns_resolver: true
              ipaclient_dns_servers:
                - 192.168.159.2
              ipareplica_setup_ca: true
              ipareplica_hidden_replica: true
            client.ipa.test:
              ipaadmin_password: SomeADMINpassword
              ipaclient_hostname: client.ipa.test
              ipaclient_no_ntp: true
              ipaclient_servers: server.ipa.test
              ipaserver_domain: ipa.test
              ipaclient_cleanup_dns_resolver: true
              ipaclient_configure_dns_resolver: true
              ipaclient_dns_servers:
                - 192.168.159.2
        """
