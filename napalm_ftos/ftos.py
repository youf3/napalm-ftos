# -*- coding: utf-8 -*-
# Copyright 2016 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Napalm driver for FTOS.

Read https://napalm.readthedocs.io for more information.
"""

import re
import socket

from napalm.base.helpers import textfsm_extractor
from napalm.base.helpers import canonical_interface_name
from napalm.base.netmiko_helpers import netmiko_args

from napalm.base import NetworkDriver
from napalm.base.exceptions import (
    ConnectionException,
    SessionLockedException,
    MergeConfigException,
    ReplaceConfigException,
    CommandErrorException,
)

# Easier to store these as constants
MINUTE_SECONDS = 60
HOUR_SECONDS = 60 * MINUTE_SECONDS
DAY_SECONDS = 24 * HOUR_SECONDS
WEEK_SECONDS = 7 * DAY_SECONDS
YEAR_SECONDS = 365 * DAY_SECONDS

class FTOSDriver(NetworkDriver):
    """NAPALM Dell Force10 FTOS Handler."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """NAPALM Dell Force10 FTOS Handler."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if optional_args is None:
            optional_args = {}

        self.netmiko_optional_args = netmiko_args(optional_args)

    def _send_command(self, command):
        """Wrapper for self.device.send.command().

        If command is a list will iterate through commands until valid command.
        """
        try:
            if isinstance(command, list):
                for cmd in command:
                    output = self.device.send_command(cmd)
                    if "% Invalid" not in output:
                        break
            else:
                output = self.device.send_command(command)
            return output
        except (socket.error, EOFError) as e:
            raise ConnectionClosedException(str(e))

    @staticmethod
    def _parse_uptime(uptime_str, short=False):
        """
        Extract the uptime string from the given FTOS Device given in form of
        32 week(s), 6 day(s), 10 hour(s), 39 minute(s)

        Return the uptime in seconds as an integer
        """
        # Initialize to zero
        (years, weeks, days, hours, minutes, seconds) = (0, 0, 0, 0, 0, 0)

        uptime_str = uptime_str.strip()
        if short:
            # until a day has passed, time is expressed in hh:mm:ss
            # after a day, time is expressed as 1d22h23m or even 20w4d21h
            # perhaps even in years at some point

            match = re.compile('^(\d+):(\d+):(\d+)$').search(uptime_str)
            if match:
                (hours, minutes, seconds) = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            else:
                match = re.compile('(\d+w)?(\d+d)?(\d+h)?(\d+m)?').search(uptime_str)
                if match:
                    for m in match.groups():
                        if m is None:
                            continue
                        elif m.endswith('y'): # year
                            years = int(m[:-1])
                        elif m.endswith('w'): # week
                            weeks = int(m[:-1])
                        elif m.endswith('d'): # day
                            days = int(m[:-1])
                        elif m.endswith('h'): # hour
                            hours = int(m[:-1])
                        elif m.endswith('m'): # minute
                            minutes = int(m[:-1])
        else:
            # in longer format, uptime is expressed in form of
            # 32 week(s), 6 day(s), 10 hour(s), 39 minute(s)
            time_list = uptime_str.split(', ')
            for element in time_list:
                if re.search("year", element):
                    years = int(element.split()[0])
                elif re.search("w(ee)?k", element):
                    weeks = int(element.split()[0])
                elif re.search("day", element):
                    days = int(element.split()[0])
                elif re.search("h(ou)?r", element):
                    hours = int(element.split()[0])
                elif re.search("min(ute)?", element):
                    minutes = int(element.split()[0])

        return (years * YEAR_SECONDS) + (weeks * WEEK_SECONDS) + \
                 (days * DAY_SECONDS) + (hours * HOUR_SECONDS) + \
                 (minutes * MINUTE_SECONDS) + seconds

    def open(self):
        """Open a connection to the device."""
        self.device = self._netmiko_open(
            'dell_force10',
            netmiko_optional_args=self.netmiko_optional_args,
        )

    def close(self):
        """Close the connection to the device."""
        self._netmiko_close()

    def get_config(self, retrieve='all'):
        """FTOS implementation of get_config."""
        config = {
            'startup': '',
            'running': '',
            'candidate': 'Not implemented for FTOS', # not implemented
        }

        if retrieve in ['all', 'running']:
            config['running'] = self._send_command("show running-config")

        if retrieve in ['all', 'startup']:
            config['startup'] = self._send_command("show startup-config")

        return config

    def get_environment(self):
        """FTOS implementation of get_environment."""
        env = {
            'fans': {},
            'temperature': {},
            'power': {},
            'cpu': {},
            'memory': {
                'available_ram': 0,
                'used_ram': 0,
            },
        }

        # get fan data
        #

        # get sensor data
        environment = self._send_command("show environment stack-unit")
        environment = textfsm_extractor(self, 'show_environment_stack-unit', environment)
        for idx, entry in enumerate(environment):
            name = "Unit %d" % int(entry['unit'])
            # temperature
            env['temperature'][name] = {
                'temperature': float(entry['temperature']),
                'is_alert': (entry['temp_status'] != '2'),
                'is_critical': (entry['temp_status'] != '2')
            }
            # power
            env['power'][name] = {
                'status': (entry['volt_status'] == 'ok'),
                'capacity': -1.0, # not implemented
                'output': -1.0, # not implemented
            }

        # get CPU data
        processes = self._send_command("show processes cpu summary")
        processes = textfsm_extractor(self, 'show_processes_cpu_summary', processes)
        for idx, entry in enumerate(processes):
            env['cpu']["Unit %d" % int(entry['unit'])] = {
                '%usage': float(entry['omin']),
            }

        # get memory data
        memory = self._send_command("show memory")
        memory = textfsm_extractor(self, "show_memory", memory)
        for idx, entry in enumerate(memory):
            env['memory']['available_ram'] += int(entry['total'])
            env['memory']['used_ram'] += int(entry['used'])

        return env

    def get_facts(self):
        """FTOS implementation of get_facts."""

        # default values.
        facts = {
            'uptime': -1,
            'vendor': u'Dell EMC',
            'os_version': 'Unknown',
            'serial_number': 'Unknown',
            'model': 'Unknown',
            'hostname': 'Unknown',
            'fqdn': 'Unknown',
            'interface_list': [],
        }

        show_ver = self._send_command("show system stack-unit 0")

        # parse version output
        for line in show_ver.splitlines():
            if line.startswith('Up Time'):
                uptime_str = line.split(': ')[1]
                facts['uptime'] = self._parse_uptime(uptime_str)
            elif line.startswith('Mfg By'):
                facts['vendor'] = line.split(': ')[1].strip()
            elif ' OS Version' in line:
                facts['os_version'] = line.split(': ')[1].strip()
            elif line.startswith('Serial Number'):
                facts['serial_number'] = line.split(': ')[1].strip()
            elif line.startswith('Product Name'):
                facts['model'] = line.split(': ')[1].strip()

        # invoke get_interfaces and list interfaces
        facts['interface_list'] = self.get_interfaces().keys()

        # get hostname from running config
        config = self.get_config('running')['running']
        for line in config.splitlines():
            if line.startswith('hostname '):
                facts['hostname'] = re.sub('^hostname ', '', line)
                facts['fqdn'] = facts['hostname']
                break

        return facts

    def get_lldp_neighbors(self):
        """FTOS implementation of get_lldp_neighbors."""

        lldp = {}
        neighbors_detail = self.get_lldp_neighbors_detail()
        for intf_name, entries in neighbors_detail.items():
            lldp[intf_name] = []
            for lldp_entry in entries:
                hostname = lldp_entry['remote_system_name']
                lldp_dict = {
                    'port': lldp_entry['remote_port_description'],
                    'hostname': hostname,
                }
                lldp[intf_name].append(lldp_dict)

        return lldp

    def get_lldp_neighbors_detail(self, interface=''):
        """FTOS implementation of get_lldp_neighbors_detail."""

        if interface:
            command = "show lldp neighbors interface {} detail".format(interface)
        else:
            command = "show lldp neighbors detail"
        lldp_entries = self._send_command(command)
        lldp_entries = textfsm_extractor(self, 'show_lldp_neighbors_detail', lldp_entries)

        lldp = {}
        for idx, lldp_entry in enumerate(lldp_entries):
            local_intf = canonical_interface_name(lldp_entry.pop('local_interface'))
            # glue multipe description lines together
            if 'remote_system_description2' in lldp_entry.keys():
                lldp_entry['remote_system_description'] += ' ' + lldp_entry['remote_system_description2'].strip()
                del lldp_entry['remote_system_description2']

            # not implemented
            lldp_entry['parent_interface'] = ''


            lldp.setdefault(local_intf, [])
            lldp[local_intf].append(lldp_entry)

        return lldp

    def get_mac_address_table(self):
        """FTOS implementation of get_mac_address_table."""

        mac_entries = self._send_command("show mac-address-table")
        mac_entries = textfsm_extractor(self, 'show_mac-address-table', mac_entries)

        mac_table = []
        for idx, entry in enumerate(mac_entries):
            entry['interface'] = canonical_interface_name(entry['interface'])
            entry['vlan'] = int(entry['vlan'])
            entry['static'] = (entry['static'] == 'Static')
            entry['active'] = (entry['active'] == 'Active')
            entry['moves'] = -1 # not implemented
            entry['last_move'] = -1 # not implemented

            mac_table.append(entry)

        return mac_table

    def get_interfaces(self):
        """FTOS implementation of get_interfaces."""

        command = "show interfaces"
        iface_entries = self._send_command(command)
        iface_entries = textfsm_extractor(self, 'show_interfaces', iface_entries)

        interfaces = {}
        for i, entry in enumerate(iface_entries):
            if len(entry['iface_name']) is 0:
                continue

            # init interface entry with default values
            iface = {
                'is_enabled': False,
                'is_up': False,
                'description': entry['description'],
                'mac_address': entry['mac_address'],
                'last_flapped': 0, # in seconds
                'speed': 0, # in megabits
            }

            # set statuses
            if entry['admin_status'] == 'up':
                iface['is_enabled'] = True
            if entry['oper_status'] == 'up':
                iface['is_up'] = True

            # parse line_speed
            speed = entry['line_speed'].split(' ')
            if speed[1] == 'Mbit':
                iface['speed'] = int(speed[0])
            elif speed[1] == 'Gbit': # not sure if this ever occurs
                iface['speed'] = int(speed[0]*1000)

            # parse last_flapped
            iface['last_flapped'] = self._parse_uptime(entry['last_flapped'])

            # add interface data to dict
            local_intf = canonical_interface_name(entry['iface_name'])
            interfaces[local_intf] = iface

        return interfaces

    def is_alive(self):
        """FTOS implementation of is_alive."""

        null = chr(0)
        if self.device is None:
            return {'is_alive': False}

        try:
            # Try sending ASCII null byte to maintain the connection alive
            self.device.write_channel(null)
            return {'is_alive': self.device.remote_conn.transport.is_active()}
        except (socket.error, EOFError):
            # If unable to send, we can tell for sure that the connection is unusable
            return {'is_alive': False}

        return {'is_alive': False}