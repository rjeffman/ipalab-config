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

For example, `mycluster.yaml` could define a cluster with three hosts, a primary server, a replica and a client, all using the default (_fedora-latest_) distro:

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

The output is a directory `simple-cluster` (defined by the attribute `lab_name`) containing a compose configuration file (`compose.yml`), compatible with Docker and Podman, an inventory file (`inventory.yml`), customized for the created environment, a `containerfiles` directory with the container files recipes to allow FreeIPA deployment in containers, and a `playbooks` directory with a `install-cluster.yml` playbook that can be used to deploy the whole cluster.

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
ansible-playbook -i inventory.yml playbooks/install-cluster.yml
```


The configuration file
----------------------

The configuration file is a YAML file with attributes used to set both the compose and inventory files.

**Global attributes**

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `lab_name` | The name of the cluster, used as the name of the target directory and to derive some other names in the compose file, for example, the _pod_ name. | yes | - |
| `containerfiles` | A list of file relative or absolute paths to container files. | no | - |
| `container_fqdn` | Convert container names to FQDN using deployment domain name. | no | false |
| `ipa_deployments` | A list of FreeIPA deployments. (See `ipa-deployments`.) | yes | - |


**ipa_deployments**

Each entry in the `ipa-deployments` list define a FreeIPA cluster. All defined hosts will be composed in the same _pod_.

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The cluster name, used to identify one cluster in the inventory file. | yes | - |
| `domain`   | The domain for the cluster. FreeIPA rules for domain names apply. | no | "ipa.test" |
| `realm`    | The realm for the cluster. | no | Uppercase `domain` |
| `admin_password` | The FreeIPA admin password. | no | "SomeADMINpassword" |
| `dm_password` | The FreeIPA LDAP Directory Manager password. | no | "SomeDMpassword" |
| `distro`   | The containerfile/image to use by default, on this deployment. | no | `fedora-latest` |
| `cluster`  | A _dict_ with the configuration for the nodes of the cluster. (See `Cluster Nodes`.) | yes | - |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |


> Note: The `dns` option will not be used on the first deployed server. This is enforced so that it is harder to end up with a deployment that has no access to external servers, so that, for example, software packages are not accessible.


**Cluster Nodes**

The cluster nodes are defined for each deployment, and may have `servers` or `clients`. At least one 'server' should always be defined. If no server or client is defined, an error is returned.

The `servers` list is a list of the servers for the deployment. The order is important, as the first server configuration will be used as the initial server, and will always have `CA` capabilities. It will also be the initial `CA renewal` server of the deployment. The other servers can have any configuration, and will be considered `replicas` (in ansible-freeipa idiom).

These are the available options to configure the first server and the replicas:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The name of the server. | yes | - |
| `hostname` | The server hostname. | no | _<server name>_._<domain>_ |
| `distro`   | The containerfile/image to use. | no | `fedora-latest` |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |
| `capabilities` | A list of capabilities to be deployed on the server. Available option are `CA`, `DNS` (nameserver), `KRA`, `AD` (AD trust), `RSN` (server only) and `HIDDEN` (replicas only). | no | For the first server `CA` is set. |
| `vars` | _Dict_ of variables to use in the deployment of the server or replica. Check (ansible-freeipa roles documentation)[https://github.com/freeipa/ansible-freeipa/tree/master/roles] for valid values | no | - |


The `clients` attribute is similar the the `servers` attribute, as it can be defined as a list of clients with its attributes, but it may also be defined with a dictionary containing:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `hosts`    | The list of client nodes.    | no | - |
| `vars` | _Dict_ of variables to use in the deployment of **all** clients. Check (ansible-freeipa ipaclient documentation)[https://github.com/freeipa/ansible-freeipa/tree/master/roles/ipaclient] for valid values | no | - |


To configure the clients, these are the available attributes:

| Name       | Description                  | Required | Default |
| :--------- | :--------------------------- | :------: | :------ |
| `name`     | The name of the client node. | yes | - |
| `hostname` | The node hostname. | no | _<server name>_._<domain>_ |
| `distro`   | The containerfile/image to use. | no | `fedora-latest` |
| `dns`      | An IP address or a node hostname to use as nameserver. | no | - |
| `vars` | _Dict_ of variables to use in the deployment of this client node. Check (ansible-freeipa ipaclient documentation)[https://github.com/freeipa/ansible-freeipa/tree/master/roles/ipaclient] for valid values | no | - |

See the available [examples](examples).


Contributing
------------

Issue tracker and repository are hosted on [Github](http://github.com/rjeffman/ipalab-config).

Use them to report issues or propose changes.


Known Issues
------------

When deploying the cluster, most of the time is spent with package downloading. To speed things up the `distro` attribute can be defined to a local distro with the packages pre-installed.

When using a custom containerfile or using multiple FreeIPA deployments, often you'll have to set `dns` due to the way container name resolution is performed, and in this case, replica deployment will not work. To circunvent this issue, use `container_fqdn: true`. (See [issue #2](https://github.com/rjeffman/ipalab-config/issues/2).)


License
-------

The code is released under the [0BSD](https://spdx.org/licenses/0BSD.html) (BSD Zero Clause License).


Author
------

Rafael Jeffman ([@rjeffman](https://github.com/rjeffman))

