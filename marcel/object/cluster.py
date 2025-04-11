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

    def __init__(self, cluster, host):
        self.cluster = cluster
        self._host = host
        self._addr = None
        self._name = None
        self._port = None

    def __repr__(self):
        self.ensure_initialized()
        return self._name if self._port is None else f'{self._name}:{self._port}'

    def __hash__(self):
        return hash(self._host)

    def __eq__(self, other):
        return self._host == other._host

    @property
    def host(self):
        return self._host

    @property
    def addr(self):
        self.ensure_initialized()
        return self._addr

    @property
    def name(self):
        self.ensure_initialized()
        return self._name

    @property
    def port(self):
        self.ensure_initialized()
        return self._port
    
    # Internal
    
    def ensure_initialized(self):
        if self._addr is None:
            if type(self._host) in (tuple, list) and len(self._host) == 2:
                self._host, self._port = self._host
            if not isinstance(self._host, str):
                raise marcel.exception.KillShellException(
                    f'Invalid host specification: {self._host}. Specify a string or 2-tuple')
            try:
                self._addr = str(ipaddress.ip_address(self._host))
                self._name = self._addr
            except ValueError:
                # self._host is not an ipv4 or ipv6 address. Proceed as if it is a host name.
                try:
                    self._addr = str(ipaddress.ip_address(socket.gethostbyname(self._host)))
                    self._name = self._host
                except socket.gaierror:
                    raise marcel.exception.KillShellException(
                        f'Cannot understand {self._host} as a host name or as an IP address.')



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
