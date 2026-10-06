Feature: Install extra packages in node images
    In order to customize the software available to lab nodes
    As a developer
    I want to specify extra packages per node

Scenario: Extra packages on IPA and external nodes
    Given the deployment configuration
    """
    lab_name: extra-packages
    external:
      hosts:
        - name: helper
          extra_packages: [rsync]
        - name: nameserver
          role: dns
          extra_packages: [bind-tools]
    ipa_deployments:
      - name: ipa
        domain: ipa.test
        cluster:
          servers:
            - name: server
              extra_packages: [jq, tmux]
          clients:
            - name: client
              extra_packages: [curl]
    """
      When I run ipalab-config
      Then the compose services have build args
        """
        server:
          extra_packages: jq tmux
        client:
          extra_packages: curl
        helper:
          extra_packages: rsync
        nameserver:
          extra_packages: bind-tools
        """
