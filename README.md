ansible-freeipa Experimentation Lab
===================================

The goal of this project is to provide a tool to create the necessary configuration to experiment with [FreeIPA](https://freeipa.org) and [ansible-freeipa](https://github.com/freeipa/ansible-freeipa) using containers.

The tool `ipalab-config` generates the necessary files to create a compose of containers (using, for example, `podman compose`) and deploy FreeIPA on it using the ansible-freeipa collection.


Installation and Usage
----------------------

The tool can be installed through `pip`:

```
pip install ipalab-config
```

To experiment with the latest branch:

```
pip install git+https://github.com/rjeffman/ipalab-config
```

Usage of Python's virtual environment is encouraged.

The only dependency for the tool is [ruamel.yaml](https://pypi.org/project/ruamel.yaml), but `ansible-core` will be required to run ansible-freeipa playbooks.

To create the configuration files simply invoke the tool with the path to the configuration file:

```
ipalab-config mycluster.yaml
```

For example, `mycluster.yaml` could define a cluster with three hosts, a primary server, a replica and a client, all using the default distro:

```yaml
---
lab_name: simple-cluster
ipa_deployments:
  - name: cluster
    domain: ipa.test
    realm:  IPA.TEST
    admin_password: SomeADMINpassword
    dm_password: SomeDMpassword
    cluster:
      servers:
        - name: server
          capabilities:
            - CA
            - DNS
        - name: replica
      clients:
        - name: client
```

The output is a directory `simple-cluster` (defined by the attribute `lab_name`) containing a compose configuration file (`compose.yml`), compatible with Docker and Podman, an inventory file (`inventory.yml`) customized for the created environment, a `containerfiles` directory with the container files recipes to allow FreeIPA deployment in containers, and a requirements file (`requirements.yml`) for Ansible if one wants to use `ansible-freeipa` to deploy the nodes.

To bring up the compose, use podman compose tool. Native `podman-compose` is provided in a separate package (`podman-compose` on Fedora) which needs to be installed in advance. Once the package is available, run:

```
podman-compose up -d
```

To run the deployment playbook you'll need Ansible and the two collections: containers.podman, to communicate with podman, and ansible-freeipa collection (again, a virtual environment is encouraged):

```
pip install ansible-core
ansible-galaxy collection install containers.podman freeipa.ansible_freeipa
```

Deploy the cluster with:

```
ansible-playbook -i inventory.yml ${HOME}/.ansible/collections/ansible_collections/freeipa/ansible_freeipa/playbooks/install-cluster.yml
```

To dispose the environment use:

```
podman-compose down
```

To automatically mount each container `/var/log` to `logs/<name>` directory, so execution can be evaluated even if the containers are offline, either set the attribute `mount_varlog` or use the CLI option `--mount-varlog`.


The configuration file
----------------------

The configuration file is a YAML file with attributes used to set both the compose and inventory files.

**Global attributes**

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `lab_name` | The name of the cluster, used as the name of the target directory and to derive some other names in the compose file, for example, the _pod_ name. | yes | - |
| `subnet`   | A CIDR representing the subnet to be used for the containers. | no | "192.168.159.0/24" |
| `containerfiles` | A list of file relative or absolute paths to container files. | no | - |
| `container_fqdn` | Convert container names to FQDN using deployment domain name. | no | false |
| `external` | A list of nodes external to the FreeIPA deployment. | no | - |
| `extra_data` | A list of files and folders to copy into the generated target directory. | no | - |
| `mount_varlog` | Mount containers '/var/log' files to be accessible from the host. | no | False |
| `ipa_deployments` | A list of FreeIPA deployments. (See `ipa-deployments`.) | yes | - |
| `network` | The name of an external network or a dict with the network configuration. | no | - |

**network**

The `network` may be defined as a string representing an external network name, and in this case, the global attribute `subnet` must be explicitly set. If the value holds a dictionary, no option is required, altought at least one value must be set.

| Name       |  Description                 | Default |
| :--------- | :--------------------------- | :------ |
| `name`     | The name of the network.     | "ipanet" |
| `subnet`   | A CIDR representing the subnet to be used for the containers. | "192.168.159.0/24" |
| `external` | When set to `true`, an external network will be used for the compose | False |
| `driver`   | The network driver to use.   | "bridge" |
| `no_dns`   | When set to `true` disables the network DNS plugin. | false |
| `dns`      | Set the address (str) or addresses (list) of DNS nameserver the network will use. | - |

**ipa_deployments**

Each entry in the `ipa-deployments` list defines a FreeIPA cluster. All defined hosts will be composed in the same _pod_.

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The cluster name, used to identify one cluster in the inventory file. | yes | - |
| `domain`   | The domain for the cluster. FreeIPA rules for domain names apply. | no | "ipalab.local" |
| `realm`    | The realm for the cluster. | no | Uppercase `domain` |
| `admin_password` | The FreeIPA admin password. | no | "SomeADMINpassword" |
| `dm_password` | The FreeIPA LDAP Directory Manager password. | no | "SomeDMpassword" |
| `distro`   | The containerfile/image to use by default, on this deployment. | no | `fedora` |
| `cluster`  | A _dict_ with the configuration for the nodes of the cluster. (See `Cluster Nodes`.) | yes | - |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |


**Cluster Nodes**

The cluster nodes are defined for each deployment, and may have `servers` or `clients`. At least one "server" should always be defined. If no server or client is defined, an error is returned.

The `servers` list is a list of the servers for the deployment. The order is important, as the first server configuration will be used as the initial server, and will always have `CA` capabilities. It will also be the initial `CA renewal` server of the deployment. The other servers can have any configuration, and will be considered `replicas` (in ansible-freeipa idiom).

These are the available options to configure the first server and the replicas:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The name of the server. | yes | - |
| `hostname` | The server hostname. | no | _<server name>_._<domain>_ |
| `distro`   | The containerfile or local image to use. | no | `fedora` |
| `image`    | The container image to use. (Overrides `distro`.) | no | - |
| `volumes`  | A list of bind volume specifications. | no | - |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |
| `capabilities` | A list of capabilities to be deployed on the server. Available option are `CA`, `DNS` (nameserver), `KRA`, `AD` (AD trust), `RSN` (server only) and `HIDDEN` (replicas only). | no | For the first server `CA` is set. |
| `memory`   | The maximum amount of memory to use defined as an integer number and a unit. The unit can be `b`, `k` or `kb`, `m` or `mb`, or `g` or `gb` (case insensitive). | no |
| `nolog`    | Do not mount `/var/log` on the host. | no | False |
| `no_limit_uid` | Do not automatically limit deployment idrange to safe values for rootless containers. Only evaluated on the first server of the deployment. | no | false |
| `vars` | _Dict_ of variables to use in the deployment of the server or replica. Check [ansible-freeipa roles documentation](https://github.com/freeipa/ansible-freeipa/tree/master/roles) for valid values | no | - |


The `clients` attribute is similar the the `servers` attribute, as it can be defined as a list of clients with its attributes, but it may also be defined with a dictionary containing:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `hosts`    | The list of client nodes.    | no | - |
| `vars` | _Dict_ of variables to use in the deployment of **all** clients. Check [ansible-freeipa ipaclient documentation](https://github.com/freeipa/ansible-freeipa/tree/master/roles/ipaclient) for valid values | no | - |


To configure the clients, these are the available attributes:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The name of the client node. | yes | - |
| `hostname` | The node hostname. | no | _<server name>_._<domain>_ |
| `distro`   | The containerfile or local image to use. | no | `fedora` |
| `image`    | The container image to use. (Overrides `distro`.) | no | - |
| `volumes`  | A list of bind volume specifications. | no | - |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |
| `nolog`      | Do not mount `/var/log` on the host. | no | False |
| `vars` | _Dict_ of variables to use in the deployment of this client node. Check [ansible-freeipa ipaclient documentation](https://github.com/freeipa/ansible-freeipa/tree/master/roles/ipaclient) for valid values | no | - |

See the available [examples](examples).

**external**

Used to define nodes external to the FreeIPA deployment.

| Name     | Description                  | Required | Default |
| :------- | :--------------------------- | :------: | :------ |
| `domain` | The domain for _all_ the external hosts.  | no | "ipalab.local" |
| `hosts`  | The list of external nodes. (See `External Nodes`) | no | - |


**External Nodes**

These are nodes that are not part of the FreeIPA deployment, and may or may not have a specific role in the environment. The following options are available:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The name of the node.        | yes | - |
| `hostname` | The node hostname. | no | _<server name>_._<domain>_ |
| `distro`   | The containerfile/image to use. | no | `fedora` |
| `volumes`   | A list of bind volume specifications. | no | - |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |
| `role`     | A specific role that will add pre-defined configuration to the node and the environment. Any `role` configuration will overwrite other options. | no | - |
| `nolog`      | Do not mount `/var/log` on the host. | no | False |
| `options`  | A dictionary of configurations specific to the available roles. | no | - |

**External Roles**

_Role `addc`_

The node with `role: addc` provides a Samba AD DC server that can be used as a Samba AD DC or to simulate, with the expected limitation, a Windows Active Directory Server. The node is provided with a very basic image, and the Samba AD DC deployment can be performed with the provided Ansible playbook `deploy_addc.yml`.

The available `vars` that can be used to customize the node through the inventory file are:

| Name   | Description       |  Default |
| :----- | :---------------- | :------- |
| `forwarder` | Should always be set to one of the available nameservers (Unbound or IPA). | - |
| `admin_pass` | The "Administrator" password. | Secret123 |
| `krb5_pass` | Samba KRB5 password. | _same as `admin_pass`_ |
| `install_packages` | If the default package list for the role is to be installed. | true |

Some other variables are inferred from the node configuration:

* ad domain: Domain part of the host name
* ad realm: `ad domain`, in uppercase.
* netbios name: First group of the hostname, in uppercase.

If using the default image configuration, to setup a trust from IPA side, use:

```
$ ipa dnsforward-zone <ad domain> --forwarder=<addc.ip_address>
$ ipa trust-add <ad domain> --admin=Administrator --password <<< <admin_pass>
```

_Role `dns`_

The node with `role: dns` provides a nameserver for the whole environment, and all the nodes in the environment will have DNS search set to use this node. The node provides the Unbound nameserver. The container accepts a volume containing the unbound configuration mounted at `/etc/unbound`. Note that the name of the main configuration file must be `unbound.conf`.

The available options for _dns_ is the `zones`, a list of zone configuration that must have a `file` attribute, with the path to a zone file, and a `name` attribute with the zone name. For _arpa zones_ (reverse zones with PTR records), instead of `name` the attribute `reverse_ip` with a network CIDR value can be used and the reverse zone name is automatically generated.

Example using zone files:

```yaml
- name: nameserver
  role: dns
  options:
    zones:
    - name: ipa.test
      file: ipa.zone
    - reverse_ip: "10.1.2.0/24"
      file: ipa_PTR.zone
```

Example using zone volumes:

```yaml
- name: nameserver
  role: dns
  volumes: ["/hostPath:/etc/unbound:Z"]
```

_Role Keycloak_

The node with `role: keycloak` provides a node with a Keycloak deployment.

Some scripts are provided under the `keycloak` directory to aid the configuration for using the node as an external identity provider (_external IdP_) for the IPA deployment. The available scripts are:

* `trust_keycloak.sh`: Must be called on all IPA nodes so that the Keycloak self-signed certificate is trusted by the node.
* `keycloak_add_oidc_client.sh`: Add on OIDC client to the Keycloak `master` realm. Requires the IPA primary server hostname, the OIDC client ID and the OIDC client password.
*  `keycloak_add_user.sh`: Add a user to the Keycloak `master` realm, given its username, email and password.

The Keycloak HTTPS server runs on port `8443` and it must be reflected on the IPA IDP configuration (`base-url`).


Output Files
------------

In the output directory the following files and directories are present:

| File  | Usage |
| :---------- | :--------------------------- |
| compose.yml | The compose file to use with `podman-compose` |
| inventory.yml | An Ansible inventory file for the cluster with ansible-freeipa variables |
| hosts | A list with ip-hostnames pairs to be added to the host `/etc/hosts` so the nodes are accessible by name |
| requirements.yml | The Ansible collection requirements to deploy the cluster |
| containerfiles | A collection of containerfiles for some Linux images where FreeIPA server and/or client is known to work with this configuration |


**About the Ansible inventory file**

The nodes in the inventory file are grouped in:

* `external`: All the hosts external to IPA deployments
* `ipaserver`: All the _first_ servers in each IPA deployment
* `ipareplicas`: All but the _first_ server in each IPA deployment
* `ipaclients`: All clients in IPA deployments
* `<deployment name>`: All IPA nodes in the IPA deployment with `name: <deployment name>`

To select a specific group of clients or server, one can use host filtering in an Ansible Playbook, for example, given two deployments `m1` and `m2`, with nodes with the same `name`, `server-1` and `server-2`, to select the `ipaserver` of deployment `m2` one could set `hosts: "ipasesrver:&m2"` on the playbook, and the playbook would only run on `server-1` of `m2`.


Playbooks
---------

It is possible to provide a set of Ansible playbooks along with the configurations files by using the `-p/--playbook` command line option. This will add any file to the output `playbooks` directory.

If passing directory as an argument to `-p`, the directory will be searched recursively for `*.yml` and `*.yaml` files and add them to the `playbooks` directory.

Note that the `playbooks` directory is flat, so if your files share the same file name, the last file will overwrite the other files with the same name.

If more complex structure of `playbooks` directory is needed, one can use global `extra_data` option in the cluster definition to copy that:

```yaml
lab_name: somelab
extra_data:
  - playbooks
```

The target directory then will contain `somelab/playbooks` as a copy of the `playbooks` folder of the source directory.


jinja2 templating
-----------------

There is optional support for jinja2 templating, it's available if jinja2 is available on the host.

The jinja2 dependency is part of the extra `opt`, and can be installed with

```
pip install ipalab-config[opt]
```

**Custom Filters**

* `ENV`:
    * Dictionary providing access to environment variables.
    * Accessing the value of an environment variable: `'{{ ENV["PWD"] }}'`
    * Accessing the value of an environment variable, with a default value in case the variable is not set: `'{{ ENV.get("CONFIG_DIR", "path/to/default") }}'`
    * If the environment variable is not set an empty value will be returned, if `get` is not used


Contributing
------------

Issue tracker and repository are hosted on [Github](https://github.com/rjeffman/ipalab-config).

Use them to report issues or propose changes.


Known Issues
------------

See [ISSUES.md](ISSUES.md)


License
-------

The code is released under the [0BSD](https://spdx.org/licenses/0BSD.html) (BSD Zero Clause License).


Author
------

Rafael Jeffman ([@rjeffman](https://github.com/rjeffman))

