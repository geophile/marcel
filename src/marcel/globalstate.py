VERSION = '0.2'


class GlobalState:

    def __init__(self, env):
        self.env = env
        self.edited_command = None
        self.version = VERSION

    def __str__(self):
        return 'GlobalState'
