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

import builtins

import marcel.argsparser
import marcel.core
import marcel.exception

HELP = '''
{L,wrap=F}cast TYPE ...

Casts elements of input tuples to the specified types.

The elements of each input tuple are cast to the specified types, except that
{n:None} is always left alone.

If the input tuple has more elements than {r:TYPE}s, then the extra elements are left alone.
'''


def cast(*functions):
    return Cast(), functions


class CastArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('gen', env)
        self.add_anon_list('types')
        self.validate()


class Cast(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.types = None
        self.functions = None

    def __repr__(self):
        return f'cast({self.types})'

    # AbstractOp

    def setup(self, env):
        # Interactive: self.types contains names of types, which can be used as conversion functions, e.g. 'str'
        # API: Should be the types themselves.
        if env.marcel_usage() == 'api':
            self.functions = self.types
        else:
            self.functions = []
            for typename in self.types:
                try:
                    type = getattr(builtins, typename)
                except Exception:
                    raise marcel.exception.KillCommandException(f'Not a valid type name: {typename}')
                self.functions.append(type)

    def receive(self, env, x):
        output = []
        n_functions = len(self.functions)
        for i, value in enumerate(x):
            try:
                cast_value = (None if value is None else
                              self.call(env, self.functions[i], value) if i < n_functions else
                              value)
                output.append(cast_value)
            except marcel.exception.KillCommandException as e:
                # This can happen if calling a marcel API function, e.g. map
                self.fatal_error(env, x, e.cause)
        self.send(env, tuple(output))
