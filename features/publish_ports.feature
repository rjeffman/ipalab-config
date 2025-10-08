Feature: Publish ports for a single server deployment
    In order to access services from the host
    As a developer
    I want to publish ports for a single server deployment

Scenario: Publish ports for a single server
    Given the deployment configuration
    """
    ipa_deployments:
      - name: single_server
        domain: ipa.test
        cluster:
          servers:
            - name: server
              publish_ports:
                - "8080:80"
                - "8443:443"
    """
    When I run ipalab-config
    Then the output directory name is "ipa-lab"
    And the ipa-lab/compose.yml file is
    """
    name: ipa-lab
    services:
      server:
        container_name: server
        restart: "no"
        cap_add:
          - SYS_ADMIN
          - DAC_READ_SEARCH
        security_opt:
          - label=disable
        hostname: server.ipa.test
        extra_hosts:
          - "server.ipa.test:192.168.159.2"
        networks:
          ipanet:
            ipv4_address: "192.168.159.2"
        image: "localhost/fedora:latest"
        build:
          context: containerfiles
          dockerfile: fedora
        ports:
          - "8080:80"
          - "8443:443"
    networks:
      ipanet:
        name: ipanet-ipa-lab
        driver: bridge
        ipam:
          config:
            - subnet: "192.168.159.0/24"
    """
