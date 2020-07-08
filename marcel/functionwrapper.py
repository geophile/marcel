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


SYMBOLS = {
    '+': marcel.reduction.r_plus,
    '*': marcel.reduction.r_times,
    '^': marcel.reduction.r_xor,
    '&': marcel.reduction.r_bit_and,
    '|': marcel.reduction.r_bit_or,
    'and': marcel.reduction.r_and,
    'or': marcel.reduction.r_or,
    'max': marcel.reduction.r_max,
    'min': marcel.reduction.r_min,
    'count': marcel.reduction.r_count,
    '.': marcel.reduction.r_group
}

# This code works around a bug in dill: https://github.com/uqfoundation/dill/issues/377.
# The workaround involves recompiling functions with source following unpickling. A function
# that doesn't have source has __globals__ other than the marcel namespace, and those functions
# appear to be immune to the bug. A function relying on the marcel namespace must have source.
# The workaround is as follows:
#
# - __init__ puts its own reference to the _function's __globals__, in _globals.
# - __getstate__ discards the _function when _source is present.
# - __call__ checks whether _function is None, and if it is, re-evals the _source, with _globals.


class FunctionWrapper:

    # For creating a Function from source, we need source and globals. If the function itself (i.e., lambda)
    # is provided, then the globals aren't needed, since we don't need to use eval.
    def __init__(self, function=None, source=None, parameterized_pipelines=None):
        self._parameterized_pipelines = [] if parameterized_pipelines is None else parameterized_pipelines
        self._op = None
        if function and source:
            self._function = function
            self._source = source
            self._display = source
        elif function:
            assert type(function) is not FunctionWrapper, function
            self._function = function
            self._source = None
            try:
                self._display = dill.source.getsource(function)
            except:
                pass
        else:  # source is not None
            self._source = source
            self._display = source
            self._function = SYMBOLS[source]
        self._globals = self._function.__globals__
        assert self._function

    def __repr__(self):
        return str(self._function) if self._display is None else self._display

    def __getstate__(self):
        if self._source:
            map = self.__dict__.copy()
            map['_function'] = None
        else:
            map = self.__dict__
        return map

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __call__(self, *args, **kwargs):
        # The function may be nested lambdas, with each level of nesting corresponding to a pipeline with
        # parameters. Apply the pipeline parameters, from outermost to innermost.
        p = len(self._parameterized_pipelines)
        f = self.function()
        while p > 0:
            p -= 1
            pipeline = self._parameterized_pipelines[p]
            if pipeline.args is not None:
                try:
                    f = f(**pipeline.args)
                except Exception as e:
                    self.handle_error(e, self.function_input_description(pipeline.args, None))
        try:
            return f(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, self.function_input_description(args, kwargs))

    def check_validity(self):
        if not callable(self.function()):
            raise marcel.exception.KillCommandException('Not a valid function')

    def source(self):
        return self._source if self._source else None

    def snippet(self):
        return self._source.split('\n')[0].strip() if self._source else self._function

    def is_grouping(self):
        return self.function() == marcel.reduction.r_group

    def set_op(self, op):
        self._op = op

    def handle_error(self, e, function_input_string):
        if self._op:
            self._op.fatal_error(function_input_string, str(e))
        else:
            raise marcel.exception.KillCommandException(f'Error evaluating {self} on {function_input_string}: {e}')

    def function(self):
        if self._function is None:
            try:
                self._function = SYMBOLS[self._source]
            except KeyError:
                self._function = eval(self._source, self._globals)
        return self._function

    @staticmethod
    def function_input_description(args, kwargs):
        function_input = []
        if args and len(args) > 0:
            function_input.append(str(args))
        if kwargs and len(kwargs) > 0:
            function_input.append(str(kwargs))
        return None if len(function_input) == 0 else ', '.join(function_input)

