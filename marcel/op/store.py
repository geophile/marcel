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

import marcel.argsparser
import marcel.core
import marcel.exception


HELP = '''
{L,wrap=F}store [-a|--append] VAR
{L,wrap=F}> VAR
{L,wrap=F}>> VAR

{L,indent=4:28}{r:-a}, {r:--append}                     Append to {r:VAR}s list, instead of replacing.

{L,indent=4:28}{r:VAR}                     The variable to be updated.

Write the incoming tuples into a list bound to {r:VAR}. By default, the current value of {r:VAR}
is replaced. If {r:--append} is specified, then it is expected that the current value
of {r:VAR} is a list, and the incoming tuples are appended. 

There is special optional syntax for the {r:store} operator: {r:store VAR} can be written as {r:> VAR}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}gen 5 | store x

stores the stream carrying {r:0, 1, 2, 3, 4} in variable {r:x}. This can also be written as:

{L,wrap=F}gen 5 > x

The symbol {r:>>} is used to append to the contents of the variable, instead of
replacing the value, e.g. {r:gen 5 >> x}. 
'''


def store(env, accumulator):
    store = Store(env)
    store.accumulator = accumulator
    return store, [None]


class StoreArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('store', env)
        self.add_flag_no_value('append', '-a', '--append')
        self.add_anon('var')
        self.validate()


class Store(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.accumulator = None
        self.append = None

    def __repr__(self):
        return f'store({self.var}, append)' if self.append else f'store({self.var})'

    def __getstate__(self):
        m = super().__getstate__()
        m['accumulator'] = self.save(self.accumulator)
        return m

    def __setstate__(self, state):
        super().__setstate__(state)
        state['accumulator'] = self.recall(state['accumulator'])
        self.__dict__.update(state)

    # AbstractOp
    
    def setup_1(self):
        if self.var is not None and self.accumulator is None:
            self.setup_interactive()
        elif self.var is None and self.accumulator is not None:
            self.setup_api()
        else:
            assert False

    def receive(self, x):
        self.accumulator.append(x)

    # For use by this class

    def setup_interactive(self):
        self.accumulator = self.getvar(self.var)
        if self.append and self.accumulator is not None:
            if not self.accumulator_is_loop_variable():
                raise marcel.exception.KillCommandException(
                    f'{self.description()} is not usable as an accumulator')
        else:
            self.accumulator = []
            self.env().setvar(self.var, self.accumulator)

    def setup_api(self):
        if self.accumulator is None:
            raise marcel.exception.KillCommandException(f'Accumulator is undefined.')
        # Test that self.accumulator is usable as an accumulator
        if not self.accumulator_is_loop_variable():
            raise marcel.exception.KillCommandException(
                f'{self.description()} is not usable as an accumulator')

    def description(self):
        return self.var if self.var else 'store\'s variable'

    def accumulator_is_loop_variable(self):
        return hasattr(self.accumulator, 'append') and hasattr(self.accumulator, '__iter__')

