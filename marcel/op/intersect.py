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

HELP = '''
{L,wrap=F}intersect PIPELINE ...

{L,indent=4:28}{r:PIPELINE}                The second input to the intersection.

The output stream represents the intersection of the tuples in the input stream, and the tuples
from the {r:PIPELINE} arguments. The tuples must be hashable, which requires that every element
of each tuple must be hashable.

Input elements from the input pipelines are considered to be the same if they are equal (in
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
        self.add_anon_list('pipelines', convert=self.check_str_or_pipeline, target='pipelines_arg')
        self.validate()


class Intersect(marcel.core.Op):

    # AbstractOp

    def __init__(self, env):
        super().__init__(env)
        self.pipelines_arg = None
        self.common = None  # item -> count: Accumulated intersection
        self.input = None   # item -> count: From one of the pipeline args

    def __repr__(self):
        return f'intersect({self.pipelines_arg})'

    def setup(self):
        for pipeline_arg in self.pipelines_arg:
            pipeline = marcel.core.PipelineWrapper.create(self.env(),
                                                          self.owner.error_handler,
                                                          pipeline_arg,
                                                          self.customize_pipeline)
            # pipeline.setup() will store item counts in self.input.
            self.input = {}
            pipeline.setup()
            pipeline.run_pipeline(None)
            # Merge input with common
            if self.common is None:
                self.common = self.input
            else:
                # Deletion has to be done after the loop. Can't modify self.common while it is being iterated.
                deleted = []
                for item, count in self.common.items():
                    input_count = self.input.get(item, 0)
                    if input_count == 0:
                        deleted.append(item)
                    elif input_count < count:
                        self.common[item] = input_count
                for item in deleted:
                    del self.common[item]

    def receive(self, x):
        try:
            count = self.common.get(x, 0)
            if count > 0:
                self.common[x] -= 1
                self.send(x)
        except TypeError:
            raise marcel.exception.KillCommandException(f'{x} is not hashable')
    # Internal

    def customize_pipeline(self, pipeline):
        def count_inputs(*x):
            try:
                input[x] = input.get(x, 0) + 1
            except TypeError:
                raise marcel.exception.KillCommandException(f'{x} is not hashable')

        input = self.input
        pipeline.append(marcel.opmodule.create_op(self.env(), 'map', count_inputs))
        return pipeline
