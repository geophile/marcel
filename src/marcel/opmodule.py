import importlib
import inspect

import marcel.op


class OpModule:

    def __init__(self, op_name, env):
        self.op_name = op_name
        self._create_op = None
        self._arg_parser = None
        op_module = importlib.import_module(f'marcel.op.{op_name}')
        # Locate items in module needed during the lifecycle of an op.
        arg_parser_function = None
        for k, v in op_module.__dict__.items():
            if k == op_name:
                # The function creating an instance of the op, e.g. ls()
                self._create_op = v
            elif inspect.isclass(v) and marcel.core.ArgParser in inspect.getmro(v):
                # The arg parser class, e.g. LsArgParser
                arg_parser_function = v
        assert arg_parser_function is not None
        self._arg_parser = arg_parser_function(env)
        assert self._create_op is not None, op_name
        assert self._arg_parser is not None, op_name

    def create_op(self):
        return self._create_op()

    def arg_parser(self):
        return self._arg_parser


def import_op_modules(env):
    op_modules = {}
    for op_name in marcel.op.public:
        op_modules[op_name] = OpModule(op_name, env)
    env.op_modules = op_modules
    return op_modules
