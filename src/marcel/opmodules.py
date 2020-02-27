import importlib

import marcel.exception
import marcel.op


class OpModules:

    def __init__(self):
        self.modules = {}
        import marcel.op
        for op_name in marcel.op.public:
            op_module = importlib.import_module('marcel.op.{}'.format(op_name))
            self.modules[op_name] = op_module

    def named(self, name):
        try:
            return self.modules[name]
        except KeyError:
            raise marcel.exception.KillCommandException('{} is not recognized as a command'.format(name))


OP_MODULES = OpModules()
