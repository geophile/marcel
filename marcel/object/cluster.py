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

import marcel.object.host


class Cluster:

    def __init__(self, name, hosts, user, identity):
        self.name = name
        self.hosts = [marcel.object.host.Host(host, self) for host in hosts]
        self.user = user
        self.identity = identity

    def __repr__(self):
        hosts = ', '.join([str(host) for host in self.hosts])
        return f'{self.name}[{hosts}]'
