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


HELP = '''
{L,wrap=F}case PREDICATE PIPELINE ... [PIPELINE]

{L,indent=4:28}{r:PREDICATE}               Used to determine if an input tuple is passed to the next PIPELINE.

{L,indent=4:28}{r:PIPELINE}                A pipeline processing input tuples for which the preceding 
PREDICATE is true.

Input tuples are sent to at most one of the PIPELINEs, and output from
all the PIPELINEs is sent downstream.

An input tuple is evaluated by each {r:PREDICATE} in turn. For the first
{r:PREDICATE} evaluating to True, the input tuple is passed to the
{r:PIPELINE} following the {r:PREDICATE}. There may be one {r:PIPELINE} at the end
without a preceding {r:PREDICATE}. This is a default case: if a tuple
evaluates to False with each {r:PREDICATE}, then the tuple is passed to
this default {r:PIPELINE}. If there is no default {r:PIPELINE}, then a tuple
evaluating to False with all predicates will not be processed further.

All {r:PIPELINE} outputs feed into the output for this operator.

Example:

{L,indent=4,wrap=F}gen 100 1 | case (x: x % 15 == 0) (| x: (x, 'FizzBuzz') |) \
                 (x: x % 3 == 0)  (| x: (x, 'Fizz') |) \
                 (x: x % 5 == 0)  (| x: (x, 'Buzz') |) \
                                  (| x: (x, x) |) \
          | sort

This implements FizzBuzz. The integers 1 .. 100 are piped to the case
operator. The predicates test for divisibility by 15, 3, and 5. It is
important to handle divisibility by 15 first, since these numbers are
also divisibly by 3 and 5, and case executes the first {r:PIPELINE} whose
{r:PREDICATE} evaluates to True. The default pipeline handles numbers not
divisible by 3, 5, or 15.
'''


def case(*args):
    return Case(), args


class CaseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env, op_name):
        super().__init__(op_name, env)
        self.add_anon_list('args', convert=self.function_or_pipeline)
        self.validate()


class Case(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.predicates = None
        self.pipelines = None
        self.args = None

    def __repr__(self):
        return 'case()'

    # AbstractOp

    def setup(self, env):
        pass
