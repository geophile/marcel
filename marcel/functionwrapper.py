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
    def __init__(self, function=None, source=None):
        self._source = None
        self._function = None
        self._op = None
        if source is None and function is not None:
            self._function = function
            try:
                self._source = dill.source.getsource(function)
            except:
                pass
        elif source is not None and function is None:
            self._function = marcel.reduction.SYMBOLS[source]
            self._source = source
        else:
            assert False

    def __repr__(self):
        return str(self._function) if self._source is None else self._source

    def __call__(self, *args, **kwargs):
        try:
            return self._function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if len(args) > 0:
                function_input.append(str(args))
            if len(kwargs) > 0:
                function_input.append(str(kwargs))
            function_input_string = None if len(function_input) == 0 else ', '.join(function_input)
            if self._op:
                self._op.fatal_error(function_input_string, str(e))
            else:
                raise marcel.exception.KillCommandException(f'Error evaluating {self} on {function_input_string}: {e}')

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
