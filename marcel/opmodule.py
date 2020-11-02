# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import importlib
import inspect

import marcel.argsparser
import marcel.core
import marcel.op


class OpModule:

    def __init__(self, op_name, env):
        self._op_name = op_name
        self._env = env
        self._api = None  # For creating op instances from the api
        self._op_constructor = None
        self._args_parser = None
        self._args_parser_constructor = None
        self._help = None
        op_module = importlib.import_module(f'marcel.op.{op_name}')
        # Locate items in module needed during the lifecycle of an op.
        for k, v in op_module.__dict__.items():
            # Leading underscore used by ops not intended for direction invocation by users.
            if k == op_name or k == '_' + op_name:
                self._api = v
            elif k == 'HELP':
                self._help = v
            else:
                isclass = inspect.isclass(v)
                if isclass:
                    parents = inspect.getmro(v)
                    if isclass and marcel.core.Op in parents:
                        # The op class, e.g.
                        if op_name == v.__name__.lower():
                            self._op_constructor = v
                        # else: Another class in the same source
                    elif isclass and marcel.argsparser.ArgsParser in parents:
                        # E.g. LsArgsParser
                        self._args_parser_constructor = v
        assert self._op_constructor is not None, op_name
        # args validator not always present, e.g. for gather

    def env(self):
        return self._env

    def op_name(self):
        return self._op_name

    def api_function(self):
        return self._api

    def create_op(self):
        return self._op_constructor(self._env)

    def args_parser(self):
        if self._args_parser is None:
            assert self._args_parser_constructor is not None
            self._args_parser = self._args_parser_constructor(self._env)
        return self._args_parser

    def help(self):
        return self._help


def import_op_modules(env):
    op_modules = {}
    for op_name in marcel.op.all:
        op_modules[op_name] = OpModule(op_name, env)
    env.op_modules = op_modules
    return op_modules


def create_op(env, op_name, *op_args):
    op_module = env.op_modules[op_name]
    op, args = op_module.api_function()(op_module.env(), *op_args)
    op_module.args_parser().parse(args, op)
    return op
