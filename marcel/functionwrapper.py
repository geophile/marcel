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

import marcel.exception
import marcel.reduction


class FunctionWrapper:

    symbols = {
        # Red args can include these functions.
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
        # Needed to support '.' notation for the red op, with grouping. Shouldn't actually be invoked.
        '.': lambda acc, x: None
    }

    # For creating a Function from source, we need source and globals. If the function itself (i.e., lambda)
    # is provided, then the globals aren't needed, since we don't need to use eval.
    def __init__(self, source=None, globals=None, function=None):
        self._source = None
        self._globals = None
        self._function = None
        self._op = None
        if source is None and globals is None and function is not None:
            self._function = function
        elif source is not None and globals is not None and function is None:
            self._source = source.strip()
            self._globals = globals

    def __repr__(self):
        return self._function if self._source is None else self._source

    def __call__(self, *args, **kwargs):
        if self._function is None:
            self.create_function()
        assert self._function is not None
        try:
            return self._function(*args, **kwargs)
        except Exception as e:
            function_input = []
            if len(args) > 0:
                function_input.append(str(args))
            if len(kwargs) > 0:
                function_input.append(str(kwargs))
            function_input_string = ', '.join(function_input)
            self._op.fatal_error(function_input_string, str(e))

    def check_validity(self):
        self.create_function()
        if not callable(self._function):
            raise marcel.exception.KillCommandException('Not a valid function')

    def source(self):
        return self._source if self.source else self._function

    def set_op(self, op):
        self._op = op

    def create_function(self):
        if self._function is None:
            self._function = FunctionWrapper.symbols.get(self._source, None)
            if self._function is None:
                if self._source is not None:
                    if self._source.split()[0] in ('lambda', 'lambda:'):
                        self._function = eval(self._source, self._globals)
                    else:
                        try:
                            self._function = eval('lambda ' + self._source, self._globals)
                        except Exception:
                            try:
                                self._function = eval('lambda: ' + self._source, self._globals)
                            except Exception:
                                raise marcel.exception.KillCommandException(
                                    f'Invalid function syntax: {self._source}')
                else:
                    raise marcel.exception.KillCommandException('Function required')
