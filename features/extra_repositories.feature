Feature: Configure additional image repositories
    In order to install packages from additional package sources
    As a developer
    I want to add repositories to individual node images

Scenario: Use repositories supported by each image distribution
    Given the deployment configuration
    """
    lab_name: extra-repositories
    external:
      hosts:
        - name: tools
          extra_repositories:
            - type: rpm
              name: tools
              baseurl: https://packages.example.test/rpm
              gpgkey: https://packages.example.test/RPM-GPG-KEY
        - name: addc
          role: addc
          extra_repositories:
            - type: copr
              project: demo/samba-tools
    ipa_deployments:
      - name: ipa
        domain: ipa.test
        cluster:
          servers:
            - name: server
              distro: fedora
              extra_repositories:
                - type: copr
                  project: demo/ipa-tools
                - type: dnf
                  repo_id: updates-testing
          clients:
            - name: client
              distro: ubuntu
              extra_repositories:
                - type: apt
                  name: vendor
                  uris: [https://packages.example.test/apt]
                  suites: [jammy]
                  components: [main]
                  key_url: https://packages.example.test/vendor-key.asc
    """
      When I run ipalab-config
      Then the compose services have repository build args
        """
        tools:
          - type: rpm
            name: tools
            baseurl: https://packages.example.test/rpm
            gpgkey: https://packages.example.test/RPM-GPG-KEY
        addc:
          - type: copr
            project: demo/samba-tools
        server:
          - type: copr
            project: demo/ipa-tools
          - type: dnf
            repo_id: updates-testing
        client:
          - type: apt
            name: vendor
            uris: [https://packages.example.test/apt]
            suites: [jammy]
            components: [main]
            key_url: https://packages.example.test/vendor-key.asc
        """

Scenario: Reject repositories unsupported by a role image
    Given the deployment configuration
    """
    lab_name: unsupported-repositories
    external:
      hosts:
        - name: nameserver
          role: dns
          extra_repositories:
            - type: rpm
              name: tools
              baseurl: https://packages.example.test/rpm
              gpgkey: https://packages.example.test/RPM-GPG-KEY
    """
      When I expect ipalab-config to fail
      Then an error ValueError occurs, with message "'extra_repositories' is not supported by Containerfile 'Containerfile'"

Scenario: Pass repository config to a custom Containerfile
    Given the deployment configuration
    """
    lab_name: custom-repositories
    containerfiles: [my-container]
    ipa_deployments:
      - name: ipa
        domain: ipa.test
        cluster:
          servers:
            - name: server
              distro: my-container
              extra_repositories:
                - type: copr
                  project: demo/custom-packages
    """
      When I run ipalab-config
      Then the compose services have repository build args
        """
        server:
          - type: copr
            project: demo/custom-packages
        """
