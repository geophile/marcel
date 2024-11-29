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
{L,wrap=F}filter [-k|--keep] [-d|--discard] [--c|--compare COMPARE] (| PIPELINE |)

{L,indent=4:28}-k, --keep              Keep input tuples that match any tuple from the PIPELINE.

{L,indent=4:28}-d, --discard           Discard input tuples that match any tuple from the PIPELINE.

{L,indent=4:28}-c, --compare           The comparison key will be computed by appying the COMPARE function
to left tuples.

{L,indent=4:28}COMPARE                 Function that computes the comparison key from a left tuple.

{L,indent=4:28}PIPELINE                Source of right tuples.

Filter the input stream based on the contents of the {r:PIPELINE}.

The input stream will be referred to as the {i:left} input, and the
stream from the {r:PIPELINE} will be referred to as the {i:right} input.

Tuples from the left input are passed to the output stream or not,
depending on a comparison between that tuple and the tuples of the right input. For
each left input tuple:

{L,indent=0:2,wrap=T}- Compute the comparison key by applying the {r:COMPARE} function to the left
tuple. If {r:COMPARE} is not provided, then the key is the entire tuple.

{L,indent=0:2,wrap=T}- If {r:--keep} is specified, and the key matches any tuple from the right
input stream, then write the left tuple to the output stream.

{L,indent=0:2,wrap=T}- If {r:--discard} is specified, and the key does not match any tuple from
the right input stream, then write the left tuple to the output
stream.

In other words, {r:--keep} is similar to set intersection, while {r:--discard}
is similar to set difference. These flags are mutually exclusive. 
If neither {r:--keep} nor {r:--discard} are specified, then {r:--keep} is assumed.
'''


# 'filter' is a builtin Python function
def filt(pipeline, compare=None, keep=False, discard=False):
    assert isinstance(pipeline, marcel.core.OpList), pipeline
    args = []
    if keep:
        args.append('--keep')
    if discard:
        args.append('--discard')
    if compare:
        args.extend(['--compare', compare])
    args.append(pipeline)
    return Filter(), args


class FilterArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('filter', env)
        self.add_flag_no_value('keep', '-k', '--keep')
        self.add_flag_no_value('discard', '-d', '--discard')
        self.add_flag_one_value('compare', '-c', '--compare')
        self.add_anon('pipelines', convert=self.check_pipeline, target='pipeline_arg')
        self.at_most_one('keep', 'discard')
        self.validate()


class Filter(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.compare = None
        self.pipeline_arg = None
        self.keep = None
        self.discard = None
        self.right = None

    def __repr__(self):
        assert self.keep != self.discard
        behavior = 'keep' if self.keep else 'discard'
        return f'filter({behavior}, {self.pipeline_arg})'

    # AbstractOp

    def setup(self, env):
        self.right = set()
        # self.discard is just for arg processing. self.keep controls execution.
        # This works if keep is already true, and if both keep and discard are false,
        # since keep is the default behavior.
        self.keep = not self.discard
        if self.compare is None:
            self.compare = lambda *x: x
        pipeline = marcel.core.Pipeline.create(self.pipeline_arg, self.customize_pipeline)
        pipeline.setup(env)
        pipeline.run_pipeline(env, None)

    def receive(self, env, x):
        c = marcel.util.wrap_op_input(self.compare(*x))
        try:
            if (c in self.right) == self.keep:
                self.send(env, x)
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
