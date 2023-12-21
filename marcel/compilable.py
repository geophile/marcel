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

import marcel.core
import marcel.parser


class Compilable(object):

    def __init__(self, env, source, compiled):
        assert source is not None
        self.env = env
        self.source = source
        self.compiled = compiled

    def __repr__(self):
        return self.source

    def recompile(self, env):
        self.env = env
        self.compiled = self.compile()
        return

    def purge(self):
        self.env = None
        self.compiled = None

    def value(self):
        assert self.env
        if self.compiled is None:
            self.compiled = self.compile()
        return self.compiled

    def compile(self):
        assert False

    @staticmethod
    def for_function(env, source, function):
        assert callable(function), function
        return CompilableFunction(env, source, function)

    @staticmethod
    def for_pipeline(env, source, pipeline):
        assert isinstance(pipeline, marcel.core.PipelineExecutable)
        return CompilablePipeline(env, source, pipeline)


class CompilableFunction(Compilable):

    def compile(self):
        assert self.env
        f = marcel.parser.Parser(self.source, self.env).parse_function()
        # The variable owning this Compilable was assigned using this marcel syntax: var = (...).
        # The function in the parens is evaluated and assigned to the var. In this case, that value is
        # itself a function. f is a function which needs to be evaluated, similar to what happened during the original
        # assign op.
        return f()

    # A function-valued env var can be called as a function. In that case, env.getvar is bypassed and the Compilable
    # is invoked directly.
    def __call__(self, *args, **kwargs):
        function = self.value()
        assert callable(function), function
        return function(*args, **kwargs)


class CompilablePipeline(Compilable):

    def compile(self):
        assert self.env
        return marcel.parser.Parser(self.source, self.env).parse_pipeline()
