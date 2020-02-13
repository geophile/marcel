import ipaddress
import socket

import osh.error


class Host:

    def __init__(self, host, cluster):
        self.host = host
        self.cluster = cluster
        try:
            self.ip_addr = str(ipaddress.ip_address(host))
            self.name = None
        except ValueError:
            # host is not an ipv4 or ipv6 address. Proceed as if it is a host name.
            try:
                self.ip_addr = str(ipaddress.ip_address(socket.gethostbyname(host)))
                self.name = host
            except socket.gaierror:
                raise osh.error.KillCommandException('Cannot understand %s as a host name or as an IP address.' % host)

    def __repr__(self):
        return self.host

    @property
    def user(self):
        return self.cluster.user
