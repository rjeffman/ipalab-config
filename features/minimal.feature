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
          ipanet-ipa-lab:
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server:
            container_name: server
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: server.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.2
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            server_only:
              children:
                ipaserver:
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
        """
      And the "ipa-lab/containerfiles" directory was copied
      And the "ipa-lab/playbooks" directory was copied

Scenario: Minimum IPA cluster
    # Note: for a minimal cluster, it is currently required that
    # the first server provides a DNS nameserver, or that contairers
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
          ipanet-ipa-lab:
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server:
            container_name: server
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: server.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.2
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
          replica:
            container_name: replica
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: replica.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.3
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
          client:
            container_name: client
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: client.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.4
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            ipa_cluster:
              children:
                ipaserver:
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
                ipareplicas:
                  hosts:
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
                      ipaclient_dns_servers: &id001
                        - 192.168.159.2
                ipaclients:
                  hosts:
                    client:
                      ipaadmin_password: SomeADMINpassword
                      ipaclient_hostname: client.ipa.test
                      ipaclient_no_ntp: true
                      ipaclient_servers: server.ipa.test
                      ipaserver_domain: ipa.test
                      ipaclient_cleanup_dns_resolver: true
                      ipaclient_configure_dns_resolver: true
                      ipaclient_dns_servers: *id001
        """
      And the "ipa-lab/containerfiles" directory was copied
      And the "ipa-lab/playbooks" directory was copied

Scenario: FQDN containers and replica capapabilities
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
          ipanet-ipa-lab:
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.159.0/24
        services:
          server.ipa.test:
            container_name: server.ipa.test
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: server.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.2
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
          replica.ipa.test:
            container_name: replica.ipa.test
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: replica.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.3
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
          client.ipa.test:
            container_name: client.ipa.test
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            security_opt:
            - label:disable
            hostname: client.ipa.test
            networks:
              ipanet-ipa-lab:
                ipv4_address: 192.168.159.4
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            ipa_cluster:
              children:
                ipaserver:
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
                ipareplicas:
                  hosts:
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
                      ipaclient_dns_servers: &id001
                        - 192.168.159.2
                      ipareplica_setup_ca: true
                      ipareplica_hidden_replica: true
                ipaclients:
                  hosts:
                    client.ipa.test:
                      ipaadmin_password: SomeADMINpassword
                      ipaclient_hostname: client.ipa.test
                      ipaclient_no_ntp: true
                      ipaclient_servers: server.ipa.test
                      ipaserver_domain: ipa.test
                      ipaclient_cleanup_dns_resolver: true
                      ipaclient_configure_dns_resolver: true
                      ipaclient_dns_servers: *id001
        """
