Feature: Use different Linux distros for nodes
    In order to test IPA against different flavors of Linux
    As a developer
    I want to select different distros and versions

Scenario: Use CentOS Stream with default tag
    Given the deployment configuration
    """
    distro: centos
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
            image: localhost/centos:latest
            build:
              context: containerfiles
              dockerfile: centos
        """

Scenario: Use CentOS Stream 10
    Given the deployment configuration
    """
    distro: centos
    tag: stream10
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
            image: localhost/centos:stream10
            build:
              context: containerfiles
              dockerfile: centos
              args:
                distro_tag: stream10
        """
Scenario: Use CentOS Stream 9
    Given the deployment configuration
    """
    distro: centos
    tag: stream9
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
            image: localhost/centos:stream9
            build:
              context: containerfiles
              dockerfile: centos
              args:
                distro_tag: stream9
        """
