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

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.opmodule
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}difference (| PIPELINE |)

{L,indent=4:28}{r:PIPELINE}                The second input to the difference.

The output stream represents the difference of the tuples in the input stream and the tuples
from the {r:PIPELINE} argument.

The input stream will be referred
to as the {i:left} input, and the stream from the {r:PIPELINE} will be
referred to as the {i:right} input.
 
A tuple is included in the output if it is present in the left input,
and not present
in the right input.
The tuples must be hashable, which requires that every element
of each tuple must be hashable.

Input elements from the two input pipelines are considered to be the same if they are equal (in
the Python sense).

Because the input pipelines may contain duplicates, the {r:difference} operator actually computes
a difference of bags. If a given tuple appears {n:n} times in the left input, and {n:m} times in
the right, then the output stream will contain {n:max(n-m, 0)} occurrences. The order of tuples in the
output is unspecified.
'''


def difference(pipeline):
    assert isinstance(pipeline, marcel.core.OpList), pipeline
    return Difference(), [pipeline]


class DifferenceArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('difference', env)
        self.add_anon('pipelines', convert=self.check_pipeline, target='pipeline_arg')
        self.validate()


class Difference(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pipeline_arg = None
        self.right = None
        self.pipeline = None
        self.first = None

    def __repr__(self):
        return f'difference({self.pipeline_arg})'

    # AbstractOp

    def setup(self, env):
        self.pipeline = marcel.core.Pipeline.create(self.pipeline_arg, self.customize_pipeline)
        self.pipeline.setup(env)
        self.first = True

    def receive(self, env, x):
        if self.first:
            self.pipeline.run_pipeline(env, None)
            self.first = False
        try:
            count = self.right.get(x, None)
            if count is not None:
                if count == 1:
                    del self.right[x]
                else:
                    self.right[x] = count - 1
            else:
                self.send(env, x)
        except TypeError:
            raise marcel.exception.KillCommandException(f'{x} is not hashable')

    def customize_pipeline(self, env, pipeline):
        def load_right(*x):
            try:
                count = self.right.get(x, None)
                self.right[x] = 1 if count is None else count + 1
            except TypeError:
                raise marcel.exception.KillCommandException(f'{x} is not hashable')

        self.right = {}
        pipeline.append(marcel.opmodule.create_op(env, 'map', load_right))
        return pipeline
