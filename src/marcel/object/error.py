import marcel.object.renderable
from marcel.util import *


class Error(marcel.object.renderable.Renderable):

    def __init__(self, cause):
        self.message = str(cause)
        self.host = None

    def __repr__(self):
        return self.render_compact()

    # Renderable

    def render_compact(self):
        return (f'Error({self.host}: {self.message})'
                if self.host else
                f'Error({self.message})')

    def render_full(self, color_scheme):
        out = self.render_compact()
        if color_scheme:
            out = colorize(out, color_scheme.error)
        return out

    # Error

    def set_host(self, host):
        self.host = host
