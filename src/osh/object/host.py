import socket
import ipaddress

import osh.error


class Host:

    def __init__(self, host):
        self.host = host
        try:
            self.ip_addr = ipaddress.ip_address(host)
            self.name = None
        except ValueError:
            # host is not an ipv4 or ipv6 address. Proceed as if it is a host name.
            try:
                self.ip_addr = ipaddress.ip_address(socket.gethostbyname(host))
                self.name = host
            except socket.gaierror:
                raise osh.error.CommandKiller('Cannot understand %s as a host name or as an IP address.' % host)

    def __repr__(self):
        return self.host
