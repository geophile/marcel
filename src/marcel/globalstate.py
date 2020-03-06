class GlobalState:

    def __init__(self, env):
        self.env = env
        self.edited_command = None

    def __str__(self):
        return 'GlobalState'
