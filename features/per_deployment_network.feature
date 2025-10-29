Feature: Per-deployment network configuration
    In order to isolate IPA deployments on separate networks
    As a developer
    I want to be able to define network configuration for each deployment individually

Scenario: Single deployment with custom network
    Given the deployment configuration
    """
    lab_name: single-deployment-network
    container_fqdn: true
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        network:
          subnet: "192.168.10.0/24"
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the single-deployment-network/compose.yml file is
    """
    name: single-deployment-network
    networks:
      ipanet-origin:
        name: ipanet-origin
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.10.0/24
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          ipanet-origin:
            ipv4_address: 192.168.10.2
        extra_hosts:
          - server.origin.ipa.test:192.168.10.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """

Scenario: Multiple deployments with mixed network configuration
    Given the deployment configuration
    """
    lab_name: mixed-network
    container_fqdn: true
    subnet: "192.168.7.0/24"
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        network:
          subnet: "192.168.10.0/24"
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
      - name: target
        domain: target.ipa.test
        admin_password: SomeOtherADMINpassword
        dm_password: SomeOtherDMpassword
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the mixed-network/compose.yml file is
    """
    name: mixed-network
    networks:
      ipanet:
        name: ipanet-mixed-network
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.7.0/24
      ipanet-origin:
        name: ipanet-origin
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.10.0/24
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          ipanet-origin:
            ipv4_address: 192.168.10.2
        extra_hosts:
          - server.origin.ipa.test:192.168.10.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
      server.target.ipa.test:
        container_name: server.target.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.target.ipa.test
        networks:
          ipanet:
            ipv4_address: 192.168.7.2
        extra_hosts:
          - server.target.ipa.test:192.168.7.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """

Scenario: Per-deployment network with custom network name
    Given the deployment configuration
    """
    lab_name: custom-name-network
    container_fqdn: true
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        network:
          name: my-custom-network
          subnet: "192.168.20.0/24"
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the custom-name-network/compose.yml file is
    """
    name: custom-name-network
    networks:
      my-custom-network:
        name: my-custom-network
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.20.0/24
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          my-custom-network:
            ipv4_address: 192.168.20.2
        extra_hosts:
          - server.origin.ipa.test:192.168.20.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """

Scenario: Multiple deployments each with their own network
    Given the deployment configuration
    """
    lab_name: isolated-networks
    container_fqdn: true
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        network:
          subnet: "192.168.10.0/24"
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
      - name: target
        domain: target.ipa.test
        admin_password: SomeOtherADMINpassword
        dm_password: SomeOtherDMpassword
        network:
          subnet: "192.168.20.0/24"
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the isolated-networks/compose.yml file is
    """
    name: isolated-networks
    networks:
      ipanet-origin:
        name: ipanet-origin
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.10.0/24
      ipanet-target:
        name: ipanet-target
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.20.0/24
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          ipanet-origin:
            ipv4_address: 192.168.10.2
        extra_hosts:
          - server.origin.ipa.test:192.168.10.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
      server.target.ipa.test:
        container_name: server.target.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.target.ipa.test
        networks:
          ipanet-target:
            ipv4_address: 192.168.20.2
        extra_hosts:
          - server.target.ipa.test:192.168.20.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """

Scenario: Per-deployment network with additional DNS options
    Given the deployment configuration
    """
    lab_name: dns-options-network
    container_fqdn: true
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        network:
          subnet: "192.168.10.0/24"
          no_dns: true
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the dns-options-network/compose.yml file is
    """
    name: dns-options-network
    networks:
      ipanet-origin:
        name: ipanet-origin
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.10.0/24
        x-podman.disable_dns: true
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          ipanet-origin:
            ipv4_address: 192.168.10.2
        extra_hosts:
          - server.origin.ipa.test:192.168.10.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """

Scenario: Backward compatibility - no per-deployment network specified
    Given the deployment configuration
    """
    lab_name: backward-compat
    container_fqdn: true
    subnet: "192.168.7.0/24"
    ipa_deployments:
      - name: origin
        domain: origin.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
      - name: target
        domain: target.ipa.test
        admin_password: SomeOtherADMINpassword
        dm_password: SomeOtherDMpassword
        cluster:
          servers:
            - name: server
              capabilities:
                - DNS
    """
    When I run ipalab-config
    Then the backward-compat/compose.yml file is
    """
    name: backward-compat
    networks:
      ipanet:
        name: ipanet-backward-compat
        driver: bridge
        ipam:
          config:
            - subnet: 192.168.7.0/24
    services:
      server.origin.ipa.test:
        container_name: server.origin.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.origin.ipa.test
        networks:
          ipanet:
            ipv4_address: 192.168.7.2
        extra_hosts:
          - server.origin.ipa.test:192.168.7.2
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
      server.target.ipa.test:
        container_name: server.target.ipa.test
        restart: no
        cap_add:
        - SYS_ADMIN
        - DAC_READ_SEARCH
        security_opt:
        - label=disable
        hostname: server.target.ipa.test
        networks:
          ipanet:
            ipv4_address: 192.168.7.3
        extra_hosts:
          - server.target.ipa.test:192.168.7.3
        image: localhost/fedora:latest
        build:
          context: containerfiles
          dockerfile: fedora
    """
