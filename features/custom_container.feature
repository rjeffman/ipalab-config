Feature: Use custom containers
    In order to test different environments
    As a developer or sysadmin
    I want to provide a custom containerfile with the cluster configuration

Scenario: Deploy server with custom containerfile
    Given the deployment configuration
    """
    lab_name: custom_container
    containerfiles: ["my-container"]
    ipa_deployments:
      - name: custom_distro
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeADMINpassword
        cluster:
          servers:
            - name: server
              distro: my-container
    """
      When I run ipalab-config
      Then the output directory name is "custom_container"
      And the custom_container/compose.yml file is
        """
        name: custom_container
        networks:
          ipanet-custom_container:
            name: ipanet-custom_container
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
              ipanet-custom_container:
                ipv4_address: 192.168.159.2
            image: localhost/my-container
            build:
              context: containerfiles
              dockerfile: my-container
        """
    And the file "my-container" is copied to directory "custom_container/containerfiles"

Scenario: Pass container file through the command line
    Given the deployment configuration
    """
    lab_name: custom_container
    ipa_deployments:
      - name: custom_distro
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeADMINpassword
        cluster:
          servers:
            - name: server
              distro: my-container
    """
    And the command line arguments "-f my-container"
      When I run ipalab-config
      Then the output directory name is "custom_container"
      And the custom_container/compose.yml file is
        """
        name: custom_container
        networks:
          ipanet-custom_container:
            name: ipanet-custom_container
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
              ipanet-custom_container:
                ipv4_address: 192.168.159.2
            image: localhost/my-container
            build:
              context: containerfiles
              dockerfile: my-container
        """
    And the file "my-container" is copied to directory "custom_container/containerfiles"
