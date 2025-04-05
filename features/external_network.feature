Feature: Allow usage of pre-exising container networks
    In order to have full control of DNS entries
    As a developer os sysadmin
    I want to be able so use a previously configured container network.

Scenario: Use an external network
    Given the deployment configuration
    """
    network: external_network
    subnet: "192.168.159.0/24"
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
          external_network:
            external: true
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
              external_network:
                ipv4_address: 192.168.159.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """

Scenario: Fail to provide 'subnet' with external network
    Given the deployment configuration
    """
    network: external_network
    ipa_deployments:
      - name: server_only
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
    """
      When I expect ipalab-config to fail
      Then an error ValueError occurs, with message "'subnet' is required for 'external' networks"
