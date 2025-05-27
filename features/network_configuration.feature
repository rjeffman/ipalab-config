Feature: Allow fine-grained configuration of the pod network
    In order to have full control the network behavior
    As a developer
    I want to be able to define the configuration of the pod network

Scenario: Configure the pod network
    Given the deployment configuration
    """
    network:
        name: custom_network
        subnet: "192.168.159.0/24"
        no_dns: true
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
          custom_network:
            name: custom_network
            driver: bridge
            ipam:
              config:
                - subnet: 192.168.159.0/24
            x-podman.disable_dns: true
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
              custom_network:
                ipv4_address: 192.168.159.2
            extra_hosts:
              - server.ipa.test:192.168.159.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """
