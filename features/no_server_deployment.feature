Feature: Deployments with no IPA server
    In order to deploy contfigurations with no IPA server
    As a developer or sysadmin
    I want to create a deployment with only clients and/or external nodes, without IPA servers

Scenario: Clients-only deployment with external KDC
    Given the deployment configuration
    """
    lab_name: localkdc
    container_fqdn: true
    subnet: "192.168.221.0/24"
    ipa_deployments:
      - name: localkdcs
        domain: localkdc.test
        cluster:
          clients:
            - name: client1
              nolog: true
              distro: fedora
            - name: client2
              nolog: true
              distro: fedora
    """
      When I run ipalab-config
      Then the output directory name is "localkdc"
      And a warning message is displayed about no servers defined for domain
      And the localkdc/compose.yml file is
        """
        name: localkdc
        networks:
          ipanet:
            name: ipanet-localkdc
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.221.0/24
        services:
          client1.localkdc.test:
            container_name: client1.localkdc.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: client1.localkdc.test
            extra_hosts:
            - client1.localkdc.test:192.168.221.2
            networks:
              ipanet:
                ipv4_address: 192.168.221.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
          client2.localkdc.test:
            container_name: client2.localkdc.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: client2.localkdc.test
            extra_hosts:
            - client2.localkdc.test:192.168.221.3
            networks:
              ipanet:
                ipv4_address: 192.168.221.3
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        """

Scenario: External hosts deployment with container_fqdn enabled
    Given the deployment configuration
    """
    lab_name: localkdc
    container_fqdn: true
    subnet: "192.168.221.0/24"
    domain: localkdc.test
    external:
      hosts:
        - name: ab
          nolog: true
          distro: fedora-localkdc
        - name: asn
          nolog: true
          distro: fedora-localkdc
    """
      When I run ipalab-config
      Then the output directory name is "localkdc"
      And a warning message is displayed about no IPA deployments
      And the localkdc/compose.yml file is
        """
        name: localkdc
        networks:
          ipanet:
            name: ipanet-localkdc
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.221.0/24
        services:
          ab.localkdc.test:
            container_name: ab.localkdc.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: ab.localkdc.test
            extra_hosts:
            - ab.localkdc.test:192.168.221.2
            networks:
              ipanet:
                ipv4_address: 192.168.221.2
            image: localhost/fedora-localkdc:latest
            build:
              context: containerfiles
              dockerfile: fedora-localkdc
          asn.localkdc.test:
            container_name: asn.localkdc.test
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: asn.localkdc.test
            extra_hosts:
            - asn.localkdc.test:192.168.221.3
            networks:
              ipanet:
                ipv4_address: 192.168.221.3
            image: localhost/fedora-localkdc:latest
            build:
              context: containerfiles
              dockerfile: fedora-localkdc
        """

Scenario: External hosts with custom containerfile
    Given the deployment configuration
    """
    lab_name: external_custom
    containerfiles: ["my-custom-kdc"]
    subnet: "192.168.222.0/24"
    domain: external.test
    external:
      hosts:
        - name: kdc1
          nolog: true
          distro: my-custom-kdc
        - name: kdc2
          nolog: true
          distro: my-custom-kdc
    """
      When I run ipalab-config
      Then the output directory name is "external_custom"
      And a warning message is displayed about no IPA deployments
      And the external_custom/compose.yml file is
        """
        name: external_custom
        networks:
          ipanet:
            name: ipanet-external_custom
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.222.0/24
        services:
          kdc1:
            container_name: kdc1
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: kdc1.external.test
            extra_hosts:
            - kdc1.external.test:192.168.222.2
            networks:
              ipanet:
                ipv4_address: 192.168.222.2
            image: localhost/my-custom-kdc:latest
            build:
              context: containerfiles
              dockerfile: my-custom-kdc
          kdc2:
            container_name: kdc2
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: kdc2.external.test
            extra_hosts:
            - kdc2.external.test:192.168.222.3
            networks:
              ipanet:
                ipv4_address: 192.168.222.3
            image: localhost/my-custom-kdc:latest
            build:
              context: containerfiles
              dockerfile: my-custom-kdc
        """
      And the file "my-custom-kdc" is copied to directory "external_custom/containerfiles"
