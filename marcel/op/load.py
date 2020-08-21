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
{L,wrap=F}load VAR
{L,wrap=F}VAR >

{L,indent=4:28}{r:VAR}                     The variable containing data to be loaded.

Write the conents of {r:VAR} to the output stream.

There is special optional syntax for the {r:load} operator: {r:load VAR} can be written as {r:VAR >}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}load foobar | map (x, y: (y, x))  

is equivalent to:

{L,wrap=F}foobar > map (x, y: (y, x))

{r:foobar >} is valid at the end of a pipeline since it produces a stream of tuples, just like
any other pipeline. So, for example the command line {r:foobar >} prints the contents of foobar,
(since the {r:out} operator is applied at the end of a top-level pipeline if not explicitly provided).

This syntax can be used in any pipeline, e.g.

{L,wrap=F}abc > join [def >]

This loads {r:abc} into the pipeline carrying data to the {r:join} operator. The other
input to {r:join} comes from loading {r:def}.
'''


def load(env, accumulator):
    load = Load(env)
    load.accumulator = accumulator
    return load, [None]


class LoadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('load', env)
        self.add_anon('var')
        self.validate()


class Load(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.accumulator = None
        self.input = None

    def __repr__(self):
        return f'load({self.var})'

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
        if self.var is not None:
            # Interactive: var is set, accumulator is None
            if not self.var.isidentifier():
                raise marcel.exception.KillCommandException(f'{self.var} is not a valid identifier')
            self.accumulator = self.getvar(self.var)
            if self.accumulator is None:
                raise marcel.exception.KillCommandException(f'Variable {self.var} is undefined.')
        else:
            # API: var is None, accumulator is set
            if self.accumulator is None:
                raise marcel.exception.KillCommandException(f'Accumulator is undefined.')
        try:
            self.input = iter(self.accumulator)
        except:
            raise marcel.exception.KillCommandException(
                f'{self.var if self.var else "Accumulator"} is not iterable.')

    def receive(self, _):
        try:
            while True:
                self.send(next(self.input))
        except StopIteration:
            pass
        self.env().mark_possibly_changed(self.var)

    def must_be_first_in_pipeline(self):
        return True
