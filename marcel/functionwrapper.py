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

import dill.source

import marcel.exception
import marcel.reduction


class FunctionWrapper:

    # For creating a Function from source, we need source and globals. If the function itself (i.e., lambda)
    # is provided, then the globals aren't needed, since we don't need to use eval.
    def __init__(self, function=None, source=None, parameterized_pipelines=[]):
        self._parameterized_pipelines = parameterized_pipelines
        self._op = None
        if function and source:
            self._function = function
            self._source = source
        elif function:
            self._function = function
            try:
                self._source = dill.source.getsource(function)
            except:
                pass
        else:  # source is not None
            self._source = source
            self._function = marcel.reduction.SYMBOLS[source]
        assert self._function

    def __repr__(self):
        return str(self._function) if self._source is None else self._source

    def __call__(self, *args, **kwargs):
        # The function may be nested lambdas, with each level of nesting corresponding to a pipeline with
        # parameters. Apply the pipeline parameters, from outermost to innermost.
        p = len(self._parameterized_pipelines)
        f = self._function
        while p > 0:
            p -= 1
            pipeline = self._parameterized_pipelines[p]
            if pipeline.args is not None and pipeline.kwargs is not None:
                try:
                    f = f(*pipeline.args, **pipeline.kwargs)
                except Exception as e:
                    self.handle_error(e, self.function_input_description(pipeline.args, pipeline.kwargs))
        try:
            return f(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, self.function_input_description(args, kwargs))

    def check_validity(self):
        if not callable(self._function):
            raise marcel.exception.KillCommandException('Not a valid function')

    def source(self):
        return self._source if self._source else None

    def snippet(self):
        return self._source.split('\n')[0].strip() if self._source else self._function

    def is_grouping(self):
        return self._function == marcel.reduction.r_group

    def set_op(self, op):
        self._op = op

    def handle_error(self, e, function_input_string):
        if self._op:
            self._op.fatal_error(function_input_string, str(e))
        else:
            raise marcel.exception.KillCommandException(f'Error evaluating {self} on {function_input_string}: {e}')

    @staticmethod
    def function_input_description(args, kwargs):
        function_input = []
        if len(args) > 0:
            function_input.append(str(args))
        if len(kwargs) > 0:
            function_input.append(str(kwargs))
        return None if len(function_input) == 0 else ', '.join(function_input)

