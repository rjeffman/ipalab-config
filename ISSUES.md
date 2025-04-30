Known issues
===========

* When deploying the cluster, most of the time is spent with package downloading. To speed things up the `distro` attribute can be defined to a local distro with the packages pre-installed.

* When deploying a cluster with replicas and clients, either add "DNS" to the first server `capabilities`, or set `container_fqdn: true`. As IPA requires hostnames to be resolvable, either option will allow the IP addresses to be known by the installers.
