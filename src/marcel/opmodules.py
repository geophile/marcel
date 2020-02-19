import importlib


class OpModules:

    def __init__(self):
        self.modules = {}
        import marcel.osh.op
        for op_name in marcel.osh.op.__all__:
            op_module = importlib.import_module('osh.op.%s' % op_name)
            self.modules[op_name] = op_module

    def named(self, name):
        try:
            return self.modules[name]
        except KeyError:
            raise marcel.osh.error.KillCommandException('%s is not recognized as a command' % name)


OP_MODULES = OpModules()
