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

import marcel.op.ifbase
import marcel.util


HELP = '''
{L,wrap=F}ifthen PREDICATE [THEN_PIPELINE]

{L,indent=4:28}{r:PREDICATE}               Used to determine if an input tuple is passed
to the {r:THEN_PIPELINE}

{L,indent=4:28}{r:THEN_PIPELINE}           This pipeline receives tuples for which 
{r:PREDICATE} evaluates to True.

Tuples arriving in the input stream are passed to the output stream. In addition, 
any tuples for which {r:PREDICATE} evaluates to True are passed to the {r:THEN_PIPELINE}.

{b:Example}

{L,indent=4,wrap=F}gen 100 | ifthen (x: x % 7 == 0) [store div7] | store all100

{r:gen 100} generates a stream of integers, 0, ..., 99.
The predicate is True for integers divisible by 7. These integers are
passed to the {r:[store div7]} pipeline, which stores the numbers in the variable {r:div7}.
All 100 integers are passed downstream to the {r:store all100} operator, which stores
the numbers in the variable {r:all100}.
'''


def ifthen(env, predicate, then):
    """
    Create a : class with the given predicate.

    Args:
        env: (todo): write your description
        predicate: (bool): write your description
        then: (todo): write your description
    """
    return Ifthen(env), [predicate, then.create_pipeline()]


class IfthenArgsParser(marcel.op.ifbase.IfBaseArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env, 'ifthen')


class Ifthen(marcel.op.ifbase.IfBase):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)

    # AbstractOp

    def receive(self, x):
        """
        Receive a message to the given value.

        Args:
            self: (todo): write your description
            x: (todo): write your description
        """
        if self.call(self.predicate, *x):
            self.then.receive(x)
        self.send(x)
