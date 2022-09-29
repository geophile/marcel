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
import marcel.object.error
import marcel.opmodule
import marcel.util

unwrap_op_output = marcel.util.unwrap_op_output

HELP = '''
{L,wrap=F}args [-a|--all] PIPELINE

{L,indent=4:28}{r:-a}, {r:--all}               Accumulate the entire input stream into a list, and bind it to a single
pipeline parameter. 

{L,indent=4:28}{r:PIPELINE}                A parameterized pipeline, to be executed with arguments coming 
from the input stream.

Items in the input stream to {r:args} will be bound to the {r:PIPELINE}s parameters. 

If the {r:PIPELINE}
has {i:n} parameters, then {i:n} items from the input stream will be used on each execution of {r:PIPELINE}.
If the input stream is exhausted after providing at least 1 but less than {i:n} arguments, remaining parameters
will be bound to {n:None}. 
'''


def args(env, pipeline_function, all=False):
    op_args = ['--all'] if all else []
    op_args.append(marcel.core.PipelineFunction(pipeline_function))
    return (Args(env)), op_args


class ArgsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('args', env)
        self.add_flag_no_value('all', '-a', '--all')
        self.add_anon('pipeline', convert=self.check_str_or_pipeline, target='pipeline_arg')
        self.validate()


class Args(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.all = None
        self.pipeline_arg = None
        self.n_params = None
        self.args = None
        self.pipeline_wrapper = None

    def __repr__(self):
        flags = 'all, ' if self.all else ''
        return f'args({flags}{self.pipeline_arg})'

    # AbstractOp

    def setup(self):
        pipeline_arg = self.pipeline_arg
        assert isinstance(pipeline_arg, marcel.core.Pipelineable)
        self.pipeline_wrapper = marcel.core.PipelineWrapper.create(self.env(),
                                                                   self.owner.error_handler,
                                                                   pipeline_arg,
                                                                   self.customize_pipeline)
        self.n_params = pipeline_arg.n_params()
        self.check_args()
        self.args = []
        self.pipeline_wrapper.setup()

    def receive(self, x):
        self.args.append(unwrap_op_output(x))
        if not self.all and len(self.args) == self.n_params:
            self.pipeline_wrapper.run_pipeline(self.args)
            self.args.clear()

    def flush(self):
        if len(self.args) > 0:
            if self.all:
                self.args = [self.args]
            else:
                while len(self.args) < self.n_params:
                    self.args.append(None)
            self.pipeline_wrapper.run_pipeline(self.args)
            self.args.clear()
        self.propagate_flush()

    def check_args(self):
        error = None
        if self.n_params == 0:
            error = 'The args pipeline must be parameterized.'
        if self.all and self.n_params > 1:
            error = 'With -a|--all option, the pipeline must have a single parameter.'
        if error:
            raise marcel.exception.KillCommandException(error)

    def customize_pipeline(self, pipeline):
        # By appending map(self.send_pipeline_output) to the pipeline, we relay pipeline output
        # to arg's downstream operator. But flush is a dead end, it doesn't propagate
        # to arg's downstream, which was the issue in bug 136.
        pipeline.append(marcel.opmodule.create_op(self.env(), 'map', self.send_pipeline_output))
        return pipeline

    def send_pipeline_output(self, *x):
        self.send(x)

