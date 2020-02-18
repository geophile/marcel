import osh.env
from osh.util import colorize


class OshError:

    def __init__(self, cause):
        self.message = str(cause)
        self.host = None

    def __repr__(self):
        description = ('Error(%s)' % self.message
                       if self.host is None else
                       'Error(%s, %s)' % (self.host, self.message))
        return colorize(description, osh.env.ENV.color_scheme().error)

    def set_host(self, host):
        self.host = host
