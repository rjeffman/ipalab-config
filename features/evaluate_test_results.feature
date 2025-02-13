Feature: Evaluate tests results
    In order to evaluate test results
    As a developer
    I want to have access to container information


Scenario: Mount /var/log in log/<node>
    Given the deployment configuration
    """
    mount_varlog: true
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
      Then the ipa-lab/compose.yml file is
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
            systemd: true
            no_hosts: true
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
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
            volumes:
              - ${PWD}/logs/server:/var/log:rw
        """

Scenario: Do not /var/log in log/<node> for selected nodes
    Given the deployment configuration
    """
    mount_varlog: true
    ipa_deployments:
      - name: server_only
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
            - name: replica
              nolog: true
    """
      When I run ipalab-config
      Then the ipa-lab/compose.yml file is
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
            systemd: true
            no_hosts: true
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
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
            volumes:
              - ${PWD}/logs/server:/var/log:rw
          replica:
            container_name: replica
            systemd: true
            no_hosts: true
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
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
        """
