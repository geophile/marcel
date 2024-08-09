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

import marcel.reduction

import dill


class Function(object):

    def __init__(self, function, source, display):
        self.function = function
        self.source = source
        self.display = display
        self.op = None

    def __repr__(self):
        return str(self.function) if self.display is None else self.display

    def __getstate__(self):
        assert False

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

    def set_globals(self, globals):
        assert False

    def snippet(self):
        return self.display.split('\n')[0].strip()

    def is_grouping(self):
        return False

    def is_count(self):
        return self.function is marcel.reduction.r_count


class NativeFunction(Function):

    def __init__(self, function):
        try:
            display = dill.source.getsource(function)
        except:
            display = str(function)
        super().__init__(function, None, display)

    def __getstate__(self):
        return self.__dict__

    def set_globals(self, globals):
        pass

    def is_grouping(self):
        # red op with grouping, via the API, represents grouping by the native function r_group.
        return self.function is marcel.reduction.r_group


class SourceFunction(Function):

    def __init__(self, function, source):
        super().__init__(function, source, source)

    def __getstate__(self):
        map = self.__dict__.copy()
        map['function'] = None
        return map

    def set_globals(self, globals):
        self.function = eval(self.source, globals)


class SymbolFunction(Function):

    FUNCTIONS = {
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
        'concat': marcel.reduction.r_concat,
        '.': marcel.reduction.r_group
    }

    def __init__(self, symbol):
        super().__init__(SymbolFunction.FUNCTIONS[symbol], symbol, symbol)

    def __getstate__(self):
        return self.__dict__

    def set_globals(self, globals):
        pass

    def is_grouping(self):
        return self.source == '.'
