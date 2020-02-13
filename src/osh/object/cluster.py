import osh.object.host


class Cluster:

    def __init__(self, name):
        self._name = name
        self._hosts = None
        self._user = None
        self._identity = None

    def __repr__(self):
        return '%s[%s]' % (self._name, ', '.join([str(host) for host in self._hosts]))

    @property
    def name(self):
        return self._name

    @property
    def hosts(self):
        return self._hosts

    @hosts.setter
    def hosts(self, hosts):
        self._hosts = [osh.object.host.Host(host, self) for host in hosts]

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user

    @property
    def identity(self):
        return self._identity

    @identity.setter
    def identity(self, identity):
        self._identity = identity
