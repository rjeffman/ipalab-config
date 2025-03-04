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
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: server.ipa.test
            networks:
              external_dns:
                ipv4_address: 192.168.53.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
            dns: 192.168.53.254
            dns_search: ipa.test
          nameserver:
            container_name: nameserver
            systemd: true
            no_hosts: true
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
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
            - ${PWD}/unbound:/etc/unbound:rw
        """
      And the ipa-lab/inventory.yml file is
        """
        ipa_lab:
          vars:
            ansible_connection: podman
          children:
            external: { hosts: { nameserver: } }
            role_dns: { hosts: { nameserver: } }
            ipa_deployments: { children: { external_dns: } }
            external_dns: { hosts: { server: } }
            ipaserver: { hosts: { server: } }
          hosts:
            nameserver:
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


Scenario: Samba AD DC
    Given the deployment configuration
    """
    lab_name: ipa-ad-trust
    subnet: "192.168.13.0/24"
    external:
      hosts:
      - name: addc
        hostname: dc.ad.ipa.test
        role: addc
        ip_address: 192.168.13.250
        options:
          forwarder: server.linux.ipa.test
          admin_pass: SomeADp4ass
          krb5_pass: SomeKRB5pass
    ipa_deployments:
      - name: ipa
        domain: linux.ipa.test
        admin_password: SomeADMINpassword
        dm_password: SomeDMpassword
        cluster:
          servers:
            - name: server
              capabilities: ["DNS", "AD"]
              vars:
                ipaserver_netbios_name: IPA
                ipaserver_idstart: 60000
                ipaserver_idmax: 62000
                ipaserver_rid_base: 63000
                ipaserver_secondary_rid_base: 70000
    """
      When I run ipalab-config
      Then the ipa-ad-trust/compose.yml file is
        """
        name: ipa-ad-trust
        services:
          addc:
            container_name: addc
            systemd: true
            no_hosts: true
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: dc.ad.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.13.250
            image: localhost/samba-addc
            build:
              context: containerfiles
              dockerfile: external-nodes
              args:
                packages: systemd
            command: /usr/sbin/init
          server:
            container_name: server
            systemd: true
            no_hosts: true
            restart: no
            cap_add:
            - SYS_ADMIN
            - DAC_READ_SEARCH
            security_opt:
            - label=disable
            hostname: server.linux.ipa.test
            networks:
              ipanet:
                ipv4_address: 192.168.13.2
            image: localhost/fedora:latest
            build:
              context: containerfiles
              dockerfile: fedora
        networks:
          ipanet:
            name: ipanet-ipa-ad-trust
            driver: bridge
            ipam:
              config:
              - subnet: 192.168.13.0/24
        """
      And the file "samba-addc/deploy_addc.yml" was copied to "ipa-ad-trust/playbooks/deploy_addc.yml"
