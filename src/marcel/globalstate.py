class GlobalState:

    def __init__(self, env):
        self.env = env
        self.edited_command = None
        self.op_modules = None

    def __str__(self):
        return 'GlobalState'

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def function_namespace(self):
        return self.env.vars()
