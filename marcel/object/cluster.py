# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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


class Host(object):

    def __init__(self, cluster, host_spec):
        self.cluster = cluster
        self.host = None
        self.addr = None
        self.name = None
        self.port = None
        if isinstance(host_spec, str):
            self.parse_host_spec(host_spec)
        elif type(host_spec) in (tuple, list) and len(host_spec) == 2:
            host_spec, port = host_spec
            self.parse_host_spec(host_spec)
            self.port = port
        else:
            raise marcel.exception.KillShellException(
                f'Invalid host specification: {host_spec}. Specify a string or 2-tuple')

    def __repr__(self):
        return self.name if self.port is None else f'{self.name}:{self.port}'

    def parse_host_spec(self, host_spec):
        self.host = host_spec
        try:
            self.addr = str(ipaddress.ip_address(host_spec))
            self.name = self.addr
        except ValueError:
            # host is not an ipv4 or ipv6 address. Proceed as if it is a host name.
            try:
                self.addr = str(ipaddress.ip_address(socket.gethostbyname(host_spec)))
                self.name = host_spec
            except socket.gaierror:
                raise marcel.exception.KillShellException(
                    f'Cannot understand {self.host} as a host name or as an IP address.')

    def __hash__(self):
        return hash(self.host)

    def __eq__(self, other):
        return self.host == other.host


# Nodes in the cluster: A cluster can comprise either one host or multiple hosts.
# It is invalid to specify values for both host and hosts.
#
# Host specification: A host (or element of hosts) is one of the following:
# - string: An IP address or hostname (str).
# - 2-tuple: An IP address or hostname (str), and a port number (int).
#
# Authentication: Authentication is done by specifying:
# - user (str), and
# - Either identity (name of a file containing a public key), or password.
# The same authentication values must be used for all nodes of the cluster.

class Cluster(object):

    def __init__(self, user, host=None, hosts=None, identity=None, password=None):
        if (host is None) == (hosts is None):
            raise marcel.exception.KillShellException(
                'Remote configuration requires the specification of host, or hosts, but not both.')
        if host is not None and type(host) in (tuple, list):
            # host=('localhost', 22) is clearly a single host with a port specified, and not a pair of hosts.
            # Allow a (str, int) tuple to be interpreted as a single host.
            if not (isinstance(host[0], str) and type(host[1] is int)):
                raise marcel.exception.KillShellException(
                    'host specification must be single-valued. Did you mean hosts?')
        if hosts is not None and type(hosts) not in (tuple, list):
            raise marcel.exception.KillShellException(
                'hosts specification must not be single-valued. Did you mean host?')
        if (identity is None) == (password is None):
            raise marcel.exception.KillShellException(
                'Remote configuration requires the specification of identity '
                '(public key file), or password, but not both.')
        if host is not None:
            hosts = [host]
        self.hosts = [Host(self, host) for host in hosts]
        self.user = user
        self.identity = identity
        self.password = password

    def __repr__(self):
        return f'Cluster({self.user} @ {self.hosts})'

    def __iter__(self):
        return iter(self.hosts)
