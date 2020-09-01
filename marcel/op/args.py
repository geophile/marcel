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


def args(env, pipeline, all=False):
    assert callable(pipeline)
    op_args = ['--all'] if all else []
    op_args.append(pipeline)
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
        self.impl = None

    def __repr__(self):
        return 'args()'

    # AbstractOp

    def setup_1(self):
        self.impl = ArgsRunnerAPI(self) if callable(self.pipeline_arg) else ArgsRunnerInteractive(self)
        self.impl.setup_1()

    def receive(self, x):
        self.impl.receive(x)

    def receive_complete(self):
        if self.impl is not None:
            self.impl.receive_complete()
            self.impl = None
        self.send_complete()


class ArgsRunner:

    def __init__(self, op):
        self.op = op
        self.all = op.all
        self.n_params = None
        self.args = None
        self.pipeline_arg = None

    def check_args(self):
        error = None
        if self.n_params == 0:
            error = 'The args pipeline must be parameterized.'
        if self.all and self.n_params > 1:
            error = 'With -a|--all option, the pipeline must have a single parameter.'
        if error:
            raise marcel.exception.KillCommandException(error)

    def receive(self, x):
        self.args.append(marcel.util.unwrap_op_output(x))
        if not self.all and len(self.args) == self.n_params:
            self.generate_and_run_pipeline()

    def receive_complete(self):
        if len(self.args) > 0:
            if self.all:
                self.args = [self.args]
            else:
                while len(self.args) < self.n_params:
                    self.args.append(None)
            self.generate_and_run_pipeline()

    def send_pipeline_output(self, *x):
        self.op.send(x)

    def generate_and_run_pipeline(self):
        assert False


class ArgsRunnerInteractive(ArgsRunner):

    def __init__(self, op):
        super().__init__(op)
        self.pipeline = None

    def setup_1(self):
        op = self.op
        if op.pipeline_arg.parameters() is None:
            raise marcel.exception.KillCommandException('The args pipeline must be parameterized.')
        self.n_params = len(op.pipeline_arg.parameters())
        self.check_args()
        self.args = []
        self.pipeline = op.pipeline_arg_value(op.pipeline_arg).copy()
        self.pipeline.set_error_handler(op.owner.error_handler)
        self.pipeline.append(marcel.opmodule.create_op(op.env(), 'map', self.send_pipeline_output))

    def generate_and_run_pipeline(self):
        self.pipeline.set_parameter_values(self.args, None)
        marcel.core.Command(None, self.pipeline).execute()
        self.args.clear()


class ArgsRunnerAPI(ArgsRunner):

    def __init__(self, op):
        super().__init__(op)

    def setup_1(self):
        self.n_params = len(self.op.pipeline_arg.__code__.co_varnames)
        self.check_args()
        self.args = []

    def generate_and_run_pipeline(self):
        op = self.op
        pipeline = op.pipeline_arg(*self.args).create_pipeline()
        pipeline.set_error_handler(op.owner.error_handler)
        pipeline.append(marcel.opmodule.create_op(op.env(), 'map', self.send_pipeline_output))
        marcel.core.Command(None, pipeline).execute()
        self.args.clear()
