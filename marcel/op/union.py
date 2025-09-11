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
{L,wrap=F}union (| PIPELINE |) ...

{L,indent=4:28}{r:PIPELINE}                The second input to the union.

The output stream represents the union of the tuples in the input stream, and the tuples
from the {r:PIPELINE} arguments.

Duplicates are maintained. If a given tuple appears {n:n} times in one input, and {n:m} times in
the other, then the output stream will contain {n:m+n} occurrences. The order of tuples in the
output is unspecified.
'''


def union(*pipelines):
    args = []
    for pipeline in pipelines:
        assert isinstance(pipeline, marcel.core.OpList), pipeline
        args.append(pipeline)
    return Union(), args


class UnionArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('union', env)
        # str: To accommodate var names
        self.add_anon_list('pipelines', convert=self.check_pipeline, target='pipelines_arg')
        self.validate()


class Union(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pipelines_arg = None
        self.pipelines = None

    def __repr__(self):
        return 'union()'

    # AbstractOp

    def setup(self, env):
        self.pipelines = []
        for pipeline_arg in self.pipelines_arg:
            pipeline = marcel.core.Pipeline.create(pipeline_arg, self.customize_pipeline)
            pipeline.setup(env)
            self.pipelines.append(pipeline)

    # Op

    def receive(self, env, x):
        self.send(env, x)

    def flush(self, env):
        for pipeline in self.pipelines:
            pipeline.run_pipeline(env, None)
        self.pipelines.clear()
        self.propagate_flush(env)

    # Internal

    def customize_pipeline(self, env, pipeline):
        # Union is implemented by passing the input stream along in receive(), and then having each pipeline's
        # arg send its output via flush. This depends on all the pipelines args having the same receiver as the
        # union op itself. However, we only want one flush after everything is done. PropagateFlushFromLast
        # makes sure that only the last pipelines propagates the flush.
        last = len(self.pipelines) == len(self.pipelines_arg) - 1
        pipeline.append(PropagateFlushFromLast(last))
        pipeline.last_op().receiver = self.receiver
        return pipeline


class PropagateFlushFromLast(marcel.core.Op):

    def __init__(self, last):
        super().__init__()
        self.last = last

    # Op

    def receive(self, env, x):
        self.send(env, x)

    def flush(self, env):
        if self.last:
            self.propagate_flush(env)