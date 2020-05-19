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

import marcel.core
import marcel.op


class OpModule:

    def __init__(self, op_name, env):
        self._op_name = op_name
        self._env = env
        self._api = None  # For creating op instances from the api
        self._constructor = None
        self._arg_parser = None
        self._arg_parser_function = None
        op_module = importlib.import_module(f'marcel.op.{op_name}')
        # Locate items in module needed during the lifecycle of an op.
        for k, v in op_module.__dict__.items():
            # Leading underscore used by ops not intended for direction invocation by users.
            if k == op_name or k == '_' + op_name:
                self._api = v
            else:
                isclass = inspect.isclass(v)
                if isclass:
                    parents = inspect.getmro(v)
                    if isclass and marcel.core.Op in parents:
                        # The op class, e.g. Ls
                        self._constructor = v
                    elif isclass and marcel.core.ArgParser in parents:
                        # The arg parser class, e.g. LsArgParser
                        self._arg_parser_function = v
        assert self._constructor is not None, op_name
        # arg parser not always present, e.g. for gather

    def op_name(self):
        return self._op_name

    def api_function(self):
        return self._api

    def create_op(self):
        return self._constructor(self._env)

    def arg_parser(self):
        if self._arg_parser is None:
            self._arg_parser = self._arg_parser_function(self._env)
        return self._arg_parser

    # The operator's help info is formatted when the arg parser is created. When the screen
    # size changes, this info has to be reformatted.
    def reformat_help(self):
        self._arg_parser = None


def import_op_modules(env):
    op_modules = {}
    for op_name in marcel.op.public:
        op_modules[op_name] = OpModule(op_name, env)
    env.op_modules = op_modules
    return op_modules
