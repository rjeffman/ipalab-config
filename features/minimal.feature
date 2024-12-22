Feature: Create minimal configuration
    In order to test FreeIPA using containers
    As a developer
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
