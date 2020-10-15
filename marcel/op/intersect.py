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
import marcel.opmodule
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}intersect PIPELINE

{L,indent=4:28}{r:PIPELINE}                The second input to the intersection.

The output stream represents the intersection of the tuples in the input stream, and the tuples
from the {r:PIPELINE} argument. The tuples must be hashable, which requires that every element
of each tuple must be hashable.

Input elements from the two input pipelines are considered to be the same if they are equal (in
the Python sense).

Because the input pipelines may contain duplicates, the {r:intersect} operator actually computes
an intersection of bags. If a given tuple appears {n:n} times in one input, and {n:m} times in
the other, then the output stream will contain {n:min(m, n)} occurrences. The order of tuples in the
output is unspecified.
'''


def intersect(env, pipeline):
    assert isinstance(pipeline, marcel.core.Pipelineable)
    return Intersect(env), [pipeline.create_pipeline()]


class IntersectArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('intersect', env)
        # str: To accommodate var names
        self.add_anon('pipeline', convert=self.check_str_or_pipeline)
        self.validate()


class Intersect(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pipeline = None
        self.right = None  # Right input, tuple -> count

    def __repr__(self):
        return f'intersect({self.pipeline})'

    # AbstractOp

    def setup(self):
        def load_right(*x):
            count = self.right.get(x, None)
            self.right[x] = 1 if count is None else count + 1
        env = self.env()
        self.right = {}
        pipeline = marcel.core.Op.pipeline_arg_value(env, self.pipeline).copy()
        pipeline.set_error_handler(self.owner.error_handler)
        pipeline.append(marcel.opmodule.create_op(env, 'map', load_right))
        marcel.core.Command(env, None, pipeline).execute()

    def receive(self, x):
        count = self.right.get(x, None)
        if count is not None:
            self.send(x)
            if count == 1:
                del self.right[x]
            else:
                self.right[x] = count - 1
