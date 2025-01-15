Feature: Provide patch to /etc/hosts file
  In order to be able to access the cluster network from the host,
  As a developer
  I want to have a patch file to apply to /etc/hosts

Scenario: Generate /etc/hosts patch for a single deployment
    Given the deployment configuration
    """
    subnet: "192.168.100.0/24"
    ipa_deployments:
      - name: ipa_cluster
        domain: ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
            - name: replica
          clients:
            - name: client
    """
     When I run ipalab-config
     Then the ipa-lab/hosts file contains
     """

     # ipalab-config hosts for 'ipa-lab'
     192.168.100.2     server.ipa.test
     192.168.100.3     replica.ipa.test
     192.168.100.4     client.ipa.test
     """

Scenario: Generate /etc/hosts patch for a multi-deployment configuration
    Given the deployment configuration
    """
    subnet: "192.168.10.0/24"
    container_fqdn: true
    ipa_deployments:
      - name: first
        domain: first.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
            - name: replica
      - name: second
        domain: second.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
            - name: replica
    """
     When I run ipalab-config
     Then the ipa-lab/hosts file contains
     """

     # ipalab-config hosts for 'ipa-lab'
     192.168.10.2      server.first.test
     192.168.10.3      replica.first.test
     192.168.10.4      server.second.test
     192.168.10.5      replica.second.test
     """
