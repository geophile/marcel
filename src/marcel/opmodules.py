import importlib

import marcel.op


class OpModules:

    def __init__(self):
        self.modules = {}
        for op_name in marcel.op.public:
            op_module = importlib.import_module(f'marcel.op.{op_name}')
            self.modules[op_name] = op_module

    def named(self, name):
        return self.modules.get(name, None)


OP_MODULES = OpModules()
