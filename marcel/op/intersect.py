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
import marcel.pipeline

HELP = '''
{L,wrap=F}intersect (| PIPELINE |) ...

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


def intersect(pipeline):
    assert isinstance(pipeline, marcel.pipeline.OpList), pipeline
    return Intersect(), [pipeline]


class IntersectArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('intersect', env)
        self.add_anon_list('pipelines', convert=self.check_pipeline)
        self.validate()


class Intersect(marcel.core.Op):

    # AbstractOp

    def __init__(self):
        super().__init__()
        self.common = None  # item -> count: Accumulated intersection
        self.input = None   # item -> count: From one of the pipelines args
        self.pipelines = None

    def __repr__(self):
        return f'intersect({self.pipelines})'

    def setup(self, env):
        for pipeline in self.pipelines:
            assert isinstance(pipeline, marcel.pipeline.Pipeline), type(pipeline)

    def receive(self, env, x):
        self.ensure_args_consumed(env)
        try:
            count = self.common.get(x, 0)
            if count > 0:
                self.common[x] -= 1
                self.send(env, x)
        except TypeError:
            raise marcel.exception.KillCommandException(f'{x} is not hashable')

    def ensure_functions_compiled(self, globals):
        for pipeline in self.pipelines:
            pipeline.ensure_functions_compiled(globals)

    # Internal

    def customize_pipelines(self, env):
        def count_inputs(*x):
            input = self.input
            try:
                input[x] = input.get(x, 0) + 1
            except TypeError:
                raise marcel.exception.KillCommandException(f'{x} is not hashable')

        customized = []
        for pipeline in self.pipelines:
            pipeline = pipeline.append_immutable(marcel.opmodule.create_op(env, 'map', count_inputs))
            customized.append(pipeline)
        self.pipelines = customized

    def ensure_args_consumed(self, env):
        if self.common is None:
            # Compute the intersection of all the pipeline args
            for pipeline in self.pipelines:
                self.input = {}
                pipeline.run_pipeline(env, {})  # Populates self.input
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
