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
{L,wrap=F}difference [-f|--filter] PIPELINE

{L,indent=4:28}-f, --filter            Filter input stream based on contents of PIPELINE stream.

{L,indent=4:28}{r:PIPELINE}                The second input to the difference.

The output stream represents the difference of the tuples in the input stream  and the tuples
from the {r:PIPELINE} argument.

The input stream will be referred
to as the {i:left} input), and the stream from the {r:PIPELINE} will be
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

This duplicate handling behavior can be modified. If {r:--filter} is specified, then the right
input is used to {i:filter} the left input. Every tuple from the left input
stream appears in the right output stream if it does not also appear in the right input stream. All of the copies
of that input tuple are written to output, or none of them are.
'''


def difference(pipeline, filter=False):
    assert isinstance(pipeline, marcel.core.Pipelineable)
    args = ['--filter'] if filter else []
    args.append(pipeline.create_pipeline())
    return Difference(), args


class DifferenceArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('difference', env)
        self.add_flag_no_value('filter', '-f', '--filter')
        self.add_anon('pipeline', convert=self.check_str_or_pipeline, target='pipeline_arg')
        self.validate()


class Difference(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.pipeline_arg = None
        self.filter = None
        self.impl = None

    def __repr__(self):
        return (f'difference(filter, {self.pipeline_arg})'
                if self.filter else
                f'difference({self.pipeline_arg})')

    # AbstractOp

    def setup(self, env):
        self.impl = DifferenceFilter(self) if self.filter else DifferenceBag(self)
        pipeline = marcel.core.PipelineWrapper.create(self.owner.error_handler,
                                                      self.pipeline_arg,
                                                      self.impl.customize_pipeline)
        pipeline.setup(env)
        pipeline.run_pipeline(env, None)

    def receive(self, env, x):
        self.impl.receive(env, x)


class DifferenceImpl(object):

    def __init__(self, op):
        self.op = op

    def customize_pipeline(self, env, pipeline):
        assert False


# Difference of bags (without --filter)
class DifferenceBag(DifferenceImpl):

    def __init__(self, op):
        super().__init__(op)
        self.right = None

    def receive(self, env, x):
        try:
            count = self.right.get(x, None)
            if count is not None:
                if count == 1:
                    del self.right[x]
                else:
                    self.right[x] = count - 1
            else:
                self.op.send(env, x)
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


# Filtering Difference (with --filter)
class DifferenceFilter(DifferenceImpl):

    def __init__(self, op):
        super().__init__(op)
        self.right = None

    def receive(self, env, x):
        try:
            if x not in self.right:
                self.op.send(env, x)
        except TypeError:
            raise marcel.exception.KillCommandException(f'{x} is not hashable')

    def customize_pipeline(self, env, pipeline):
        def load_right(*x):
            try:
                self.right.add(x)
            except TypeError:
                raise marcel.exception.KillCommandException(f'{x} is not hashable')

        self.right = set()
        pipeline.append(marcel.opmodule.create_op(env, 'map', load_right))
        return pipeline
