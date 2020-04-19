import marcel.object.renderable


class Error(marcel.object.renderable.Renderable):

    def __init__(self, cause):
        self.message = str(cause)
        self.label = None

    def __repr__(self):
        return self.render_compact()

    # Renderable

    def render_compact(self):
        return (f'Error({self.message})'
                if self.label is None else
                f'Error({self.label}: {self.message})')

    def render_full(self, color_scheme):
        out = self.render_compact()
        if color_scheme:
            out = marcel.util.colorize(out, color_scheme.error)
        return out

    # Error

    def set_label(self, label):
        self.label = label
