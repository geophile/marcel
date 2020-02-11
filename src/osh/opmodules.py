import importlib

import osh.error


class OpModules:

    def __init__(self):
        self.modules = {}
        import osh.op
        for op_name in osh.op.__all__:
            op_module = importlib.import_module('osh.op.%s' % op_name)
            self.modules[op_name] = op_module

    def named(self, name):
        try:
            return self.modules[name]
        except KeyError:
            raise osh.error.KillCommandException('%s is not recognized as a command' % name)


OP_MODULES = OpModules()
