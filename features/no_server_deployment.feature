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
