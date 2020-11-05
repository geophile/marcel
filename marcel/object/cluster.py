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
        """
        Initialize a host.

        Args:
            self: (todo): write your description
            host: (str): write your description
            cluster: (str): write your description
        """
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
        """
        Return the repr representation of this instruction.

        Args:
            self: (todo): write your description
        """
        return self.addr if self.name is None else self.name

    def __hash__(self):
        """
        Return the hash of the host.

        Args:
            self: (todo): write your description
        """
        return hash(self.host)

    def __eq__(self, other):
        """
        Return true if other is equal false otherwise false.

        Args:
            self: (todo): write your description
            other: (todo): write your description
        """
        return self.host == other.host

    @property
    def user(self):
        """
        Return a user s user.

        Args:
            self: (todo): write your description
        """
        return self.cluster.user


class Cluster:

    def __init__(self, user, identity=None, host=None, hosts=None):
        """
        Initialize the connection.

        Args:
            self: (todo): write your description
            user: (str): write your description
            identity: (todo): write your description
            host: (str): write your description
            hosts: (str): write your description
        """
        if (host is None) == (hosts is None):
            raise marcel.exception.KillShellException(
                'Remote configuration requires the specification of host, or hosts, but not both.')
        if host is not None and type(host) in (tuple, list):
            raise marcel.exception.KillShellException(
                'host specification must be single-valued. Did you mean hosts?')
        if hosts is not None and type(hosts) not in (tuple, list):
            raise marcel.exception.KillShellException(
                'host specification must not be single-valued. Did you mean host?')
        if host is not None:
            hosts = [host]
        self.hosts = [Host(host, self) for host in hosts]
        self.user = user
        self.identity = identity

    def __repr__(self):
        """
        Return a human - readable string.

        Args:
            self: (todo): write your description
        """
        hosts = ', '.join([str(host) for host in self.hosts])
        return f'Cluster({self.user}, {hosts})'
