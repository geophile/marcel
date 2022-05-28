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
import marcel.picklefile
import marcel.reservoir


HELP = '''
{L,wrap=F}load VAR
{L,wrap=F}VAR >$

{L,indent=4:28}{r:VAR}                        An environment variable or file.

Write the contents of the environment variable {r:VAR} to the output stream.

There is special optional syntax for the {r:load} operator: {r:load VAR} can be written as {r:VAR >$}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}load foobar | map (x, y: (y, x))  

is equivalent to:

{L,wrap=F}foobar >$ map (x, y: (y, x))

{r:foobar >$} is valid at the beginning of a pipeline since it produces a stream of tuples, just like
any other pipeline. So, for example the command line {r:foobar >$} prints the contents of foobar,
(since the {r:write} operator is applied at the end of a top-level pipeline if not explicitly provided).

This syntax can be used in any pipeline, e.g.

{L,wrap=F}abc >$ join [def >$]

This loads {r:abc} into the pipeline carrying data to the {r:join} operator. The other
input to {r:join} comes from loading {r:def}.
'''


def load(env, target):
    load = Load(env)
    if type(target) not in (str, marcel.reservoir.Reservoir):
        raise marcel.exception.KillCommandException(f'{target} is not a Reservoir: {type(target)}')
    return load, [target]


class LoadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('load', env)
        self.add_anon('var')
        self.validate()


class Load(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.var = None
        self.picklefile = None
        self.reader = None

    def __repr__(self):
        return f'load({self.var})'

    # AbstractOp

    def setup(self):
        if type(self.var) is marcel.reservoir.Reservoir:
            # API
            self.picklefile = self.var
        elif type(self.var) is str:
            # Interactive
            if self.var.isidentifier():
                self.picklefile = self.getvar(self.var)
                if self.picklefile is None:
                    raise marcel.exception.KillCommandException(f'Variable {self.var} is undefined.')
                if type(self.picklefile) is not marcel.reservoir.Reservoir:
                    raise marcel.exception.KillCommandException(f'Variable {self.var} is not a Reservoir.')
                self.env().mark_possibly_changed(self.var)
            else:
                raise marcel.exception.KillCommandException(f'{self.var} is not a Python identifier.')
        elif self.var is not None:
            raise marcel.exception.KillCommandException(
                f'The type of {self.var} is {type(self.var)}. Only a Reservoir can be loaded')
        self.reader = iter(self.picklefile)

    def run(self):
        try:
            while True:
                self.send(next(self.reader))
        except StopIteration:
            self.reader.close()
        except:
            self.reader.close()
            raise

    def must_be_first_in_pipeline(self):
        return True
