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

import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.picklefile
import marcel.reservoir


HELP = '''
{L,wrap=F}load TARGET
{L,wrap=F}TARGET >

{L,indent=4:28}{r:TARGET}                     An environment variable or file.

Write the contents of {r:TARGET} to the output stream.

A {r:TARGET} is either an environment variable
or a file. A variable is indicated by a Python identifier, and any other string identifies a file.
(So {n:abc} is an identifier, while {n:./abc} is a file in the current directory.) 

There is special optional syntax for the {r:load} operator: {r:load TARGET} can be written as {r:TARGET >}. 
With this alternative syntax, the {r:>} acts as a pipe ({r:|}). So, for example, the following command:

{L,wrap=F}load foobar | map (x, y: (y, x))  

is equivalent to:

{L,wrap=F}foobar > map (x, y: (y, x))

{r:foobar >} is valid at the beginning of a pipeline since it produces a stream of tuples, just like
any other pipeline. So, for example the command line {r:foobar >} prints the contents of foobar,
(since the {r:out} operator is applied at the end of a top-level pipeline if not explicitly provided).

This syntax can be used in any pipeline, e.g.

{L,wrap=F}abc > join [def >]

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
        self.add_anon('target')
        self.validate()


class Load(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.target = None
        self.picklefile = None
        self.reader = None

    def __repr__(self):
        return f'load({self.target})'

    # AbstractOp

    def setup(self):
        if type(self.target) is marcel.reservoir.Reservoir:
            # API
            self.picklefile = self.target
        elif type(self.target) is str:
            # API: string is a filename.
            # Interactive: string is a filename or environment variable name.
            if self.target.isidentifier():
                self.picklefile = self.getvar(self.target)
                if self.picklefile is None:
                    raise marcel.exception.KillCommandException(f'Variable {self.target} is undefined.')
                if type(self.picklefile) is not marcel.reservoir.Reservoir:
                    raise marcel.exception.KillCommandException(f'Variable {self.target} is not a Reservoir.')
                self.env().mark_possibly_changed(self.target)
            else:
                if pathlib.Path(self.target).exists():
                    self.picklefile = marcel.picklefile.PickleFile(self.target)
                else:
                    raise marcel.exception.KillCommandException(f'{self.target} does not exist.')
        elif self.target is not None:
            raise marcel.exception.KillCommandException(f'Reservoir is undefined.')
        else:
            raise marcel.exception.KillCommandException(f'{self.picklefile} is not a Reservoir.')
        self.reader = iter(self.picklefile)

    def receive(self, _):
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
