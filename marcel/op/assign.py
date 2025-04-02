# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import marcel.argsparser
import marcel.compilable
import marcel.core
import marcel.exception
import marcel.function

Compilable = marcel.compilable.Compilable


def assign(var, value):
    return Assign(), [var, value]


class AssignArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__(self, env)
        self.add_anon('var')
        self.add_anon('value')
        self.validate()


class Assign(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.var = None
        self.string = None
        self.pipeline = None
        self.function = None
        self.value = None
        self.source = None

    def __repr__(self):
        return f'assign({self.var}, {self.value})'

    # AbstractOp

    def setup(self, env):
        if self.string is not None:
            assert isinstance(self.string, str), type(self.string)
            self.value = self.string
        if self.pipeline is not None:
            assert type(self.pipeline) is marcel.core.PipelineExecutable, type(self.pipeline)
            self.value = self.pipeline
        if self.function is not None:
            assert isinstance(self.function, marcel.function.Function), type(self.function)
            self.value = self.call(env, self.function)
        if isinstance(self.value, marcel.function.Function):
            self.value.set_globals(env.vars())

    def run(self, env):
        # The fix for bug 267 is to use function.source, which may have an extra lambda added on to the
        # front (for situations such as "inc = (lambda f: f + 1)"). But also allow for self.function to
        # not have source, or for it to be None.
        source = None
        try:
            source = self.function.source
        except AttributeError:
            pass
        if source is None:
            source = self.source
        env.setvar_with_source(self.var, self.value, source)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True

    # Assign
    
    def set_var_and_value(self, var, value, source):
        assert var is not None
        assert value is not None
        self.var = var
        self.source = source
        if callable(value):
            self.function = value
        elif type(value) is marcel.core.PipelineExecutable:
            self.pipeline = value
        elif isinstance(value, str):
            self.string = value
        else:
            assert False, value
