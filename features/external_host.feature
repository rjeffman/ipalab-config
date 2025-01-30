Feature: Configure external hosts to the IPA cluster
    In order to test interoperability with other systems,
    As a developer
    I want to configure hosts with specific characteristics
        which are not part of the IPA deployments.

Scenario: External DNS
    Given the deployment configuration
    """
    network: external_dns
    subnet: "192.168.53.0/24"
    external:
      domain: ipa.test
      hosts:
      - name: nameserver
        hostname: unbound.ipa.test
        ip_address: 192.168.53.254
        role: dns
        options:
          zones:
            - name: ipa.test
              file: "unbound/ipa.test"
            - name: 53.168.192.in-addr.arpa
              file: "unbound/53.168.192.in-addr.arpa.zone"
    ipa_deployments:
      - name: external_dns
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
          external_dns:
            external: true
        services:
          server:
            container_name: server
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label:disable
            hostname: server.ipa.test
            networks:
              external_dns:
                ipv4_address: 192.168.53.2
            image: localhost/fedora-latest
            build:
              context: containerfiles
              dockerfile: fedora-latest
            dns: 192.168.53.254
            dns_search: ipa.test
          nameserver:
            container_name: nameserver
            systemd: true
            no_hosts: true
            restart: never
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label:disable
            hostname: unbound.ipa.test
            networks:
              external_dns:
                ipv4_address: 192.168.53.254
            image: localhost/unbound
            build:
              context: unbound
              dockerfile: Containerfile
            dns: 192.168.53.254
            dns_search: ipa.test
            volumes:
            - ${PWD}/unbound:/etc/unbound:Z
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            external:
              children:
                role_dns:
                  hosts:
                    nameserver:
            external_dns:
              children:
                ipaserver:
                  hosts:
                    server:
                      ipaserver_hostname: server.ipa.test
                      ipaadmin_password: SomeADMINpassword
                      ipadm_password: SomeDMpassword
                      ipaserver_domain: ipa.test
                      ipaserver_realm: IPA.TEST
                      ipaclient_no_ntp: false
                      ipaserver_setup_firewalld: false
                      ipaserver_no_host_dns: true
        """
      And the ipa-lab/hosts file contains
        """

        # ipalab-config hosts for 'ipa-lab'
        192.168.53.254    unbound.ipa.test
        192.168.53.2      server.ipa.test
        """
      And the ipa-lab/unbound/zones.conf file contains
        """
        auth-zone:
            name: ipa.test
            zonefile: /etc/unbound/zones/ipa.test
            for-downstream: yes
            for-upstream: no

        auth-zone:
            name: 53.168.192.in-addr.arpa
            zonefile: /etc/unbound/zones/53.168.192.in-addr.arpa.zone
            for-downstream: yes
            for-upstream: no
        """
      And the ipa-lab/unbound/domains file contains
        """
        private-domain: ipa.test
        """
      And the ipa-lab/unbound/access_control file contains
        """
        access-control: 192.168.53.0/24 allow
        """
      And the "ipa-lab/unbound" directory was copied
      And the file "unbound/ipa.test" was copied to "ipa-lab/unbound/zones/ipa.test"
