[![Build Status](https://travis-ci.com/napalm-automation-community/napalm-ftos.svg?branch=master)](https://travis-ci.org/napalm-automation-community/napalm-ftos)
[![PyPI](https://img.shields.io/pypi/v/napalm-ftos.svg)](https://pypi.python.org/pypi/napalm-ftos)
[![Supported python versions](https://img.shields.io/pypi/pyversions/napalm-ftos.svg)](https://pypi.python.org/pypi/napalm-ftos/)

# napalm-ftos

NAPALM driver for Dell EMC/Force10 FTOS

### Implemented APIs

* close
* cli
* get_arp_table
* get_bgp_neighbors_detail
* get_config
* get_environment
* get_facts
* get_interfaces
* get_interfaces_counters
* get_interfaces_ip
* get_lldp_neighbors
* get_lldp_neighbors_detail
* get_mac_address_table
* get_ntp_peers
* get_ntp_servers
* get_route_to
* get_ntp_stats
* get_snmp_information
* get_users
* is_alive
* open
* ping
* traceroute

### Missing APIs.

* commit_config
* compare_config
* compliance_report
* connection_tests
* discard_config
* get_bgp_config
* get_bgp_neighbors
* get_firewall_policies
* get_ipv6_neighbors_table
* get_network_instances
* get_optics
* get_probes_config
* get_probes_results
* load_merge_candidate
* load_replace_candidate
* load_template
* post_connection_tests
* pre_connection_tests
* rollback
