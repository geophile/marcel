class Cluster:

    def __init__(self, name):
        self._name = name
        self._hosts = None
        self._user = None
        self._identity = None

    def __repr__(self):
        return '%s[%s]' % (self._name, ', '.join(self._hosts))

    @property
    def name(self):
        return self._name

    @property
    def hosts(self):
        return self._hosts

    @hosts.setter
    def hosts(self, x):
        self._hosts = x

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, x):
        self._user = x

    @property
    def identity(self):
        return self._identity

    @identity.setter
    def identity(self, x):
        self._identity = x
