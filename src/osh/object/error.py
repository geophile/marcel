import osh.env
import osh.object.renderable
from osh.util import colorize


class OshError(osh.object.renderable.Renderable):

    def __init__(self, cause):
        self.message = str(cause)
        self.host = None

    def __repr__(self):
        return self.render_compact()

    # Renderable

    def render_compact(self):
        return ('Error(%s)' % self.message
                if self.host is None else
                'Error(%s, %s)' % (self.host, self.message))

    def render_full(self, color):
        out = self.render_compact()
        if color:
            out = colorize(out, osh.env.ENV.color_scheme().error)
        return out

    # OshError

    def set_host(self, host):
        self.host = host
