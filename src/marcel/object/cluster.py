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
