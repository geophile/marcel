# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import ipaddress
import socket

import marcel.exception
import marcel.util


class Host:

    def __init__(self, host, cluster):
        self.host = host
        self.cluster = cluster
        try:
            self.addr = str(ipaddress.ip_address(host))
            self.name = None
        except ValueError:
            # host is not an ipv4 or ipv6 address. Proceed as if it is a host name.
            try:
                self.addr = str(ipaddress.ip_address(socket.gethostbyname(host)))
                self.name = host
            except socket.gaierror:
                raise marcel.exception.KillCommandException(
                    f'Cannot understand {host} as a host name or as an IP address.')

    def __repr__(self):
        return self.addr if self.name is None else self.name

    @property
    def user(self):
        return self.cluster.user


class Cluster:

    def __init__(self, name, user, identity, hosts):
        self.name = name
        self.hosts = [Host(host, self) for host in hosts]
        self.user = user
        self.identity = identity

    def __repr__(self):
        hosts = ', '.join([str(host) for host in self.hosts])
        return f'{self.name}[{hosts}]'


def define_remote(name, user, identity, host, hosts):
    if host is not None and hosts is not None:
        raise marcel.exception.KillShellException(
            f'Remote access to {name} requires specification of one host or a list of hosts, but not both')
    if host is None and hosts is None:
        raise marcel.exception.KillShellException(
            f'Remote access to {name} requires specification of one host or a list of hosts')
    if host is not None and marcel.util.is_sequence_except_string(host):
        raise marcel.exception.KillShellException(
            f'Remote access to {name}: host must not be a list. Did you mean hosts?')
    if hosts is not None and not marcel.util.is_sequence_except_string(hosts):
        raise marcel.exception.KillShellException(
            f'Remote access to {name}: hosts must not be a list. Did you mean host?')
    if host is not None:
        hosts = [host]
    return marcel.object.cluster.Cluster(name, user, identity, hosts)
