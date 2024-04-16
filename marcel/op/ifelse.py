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

import marcel.core
import marcel.op.ifbase
import marcel.util


HELP = '''
{L,wrap=F}ifelse PREDICATE (| THEN_PIPELINE |)

{L,indent=4:28}{r:PREDICATE}               Used to determine if an input tuple is passed
to the {r:THEN_PIPELINE}

{L,indent=4:28}{r:THEN_PIPELINE}           This pipelines receives tuples for which 
{r:PREDICATE} evaluates to True.

{r:PREDICATE} is applied to each input tuple. If the {r:PREDICATE} evaluates to
True, then the tuple is passed to the {r:THEN_PIPELINE}. Otherwise, 
the tuple is passed downstream.

{b:Example}

{L,indent=4,wrap=F}gen 100 | ifelse (x: x % 2 == 0) (| store even |) | store odd

{r:gen 100} generates a stream of integers, 0, ..., 99.
The predicate is True for even integers. These integers are
passed to the {r:[store even]} pipelines, which stores the numbers in the variable {r:even}.
Odd integers only are passed downstream, to {r:store odd} which stores numbers in the {r:odd}
variable. 
'''


def ifelse(predicate, then):
    assert isinstance(then, marcel.core.OpList), then
    return Ifelse(), [predicate, then]


class IfelseArgsParser(marcel.op.ifbase.IfBaseArgsParser):

    def __init__(self, env):
        super().__init__(env, 'ifelse')


class Ifelse(marcel.op.ifbase.IfBase):

    def __init__(self):
        super().__init__()

    # AbstractOp

    def receive(self, env, x):
        if self.call(env, self.predicate, *x):
            self.then.receive(env, x)
        else:
            self.send(env, x)
