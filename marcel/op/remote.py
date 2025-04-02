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

import subprocess
import io
import sys

import dill

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.cluster
import marcel.object.error
import marcel.op.forkmanager
import marcel.util

HELP = '''
{L,wrap=F}remote CLUSTER (| PIPELINE |)

{L,indent=4:28}{r:CLUSTER}                The name of a cluster.
   
{L,indent=4:28}{r:PIPELINE}                A pipelines whose instances are to be executed on nodes
of the cluster.

The pipeline is executed on each node of the named cluster. Output comprises 
the output streams from each node, labelled 
with the node's name.

Example:

{p,indent=4,wrap=F}
remote lab (| gen 3 |)

{r:lab} is a cluster, configured in the marcel startup script. The pipeline {r:gen 3}
is run on each node of this cluster. The output from each node is returned, and a label
identifying the node is prepended to each output tuple. So if {r:lab} consists of two nodes,
{R:lab1} and {r:lab2},
the output might look like this:

{p,indent=4,wrap=F}
(lab1, 0)
(lab2, 0)
(lab2, 1)
(lab1, 1)
(lab1, 2)
(lab2, 2)
'''


def remote(cluster, pipeline):
    assert isinstance(pipeline, marcel.core.OpList), pipeline
    pipeline_arg = marcel.core.PipelineFunction(pipeline) if callable(pipeline) else pipeline
    return Remote(), [cluster, pipeline_arg]


# For API
class RemoteArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('remote', env)
        self.add_anon('cluster', convert=self.cluster)
        self.add_anon('pipeline', convert=self.check_pipeline, target='pipeline_arg')
        self.validate()


class Remote(marcel.core.Op):

    class LabelThread(marcel.core.Op):

        ID_COUNTER = 0

        def __init__(self, label):
            super().__init__()
            self.label_list = [label]
            self.label_tuple = (label,)
            self.id = Remote.LabelThread.next_id()

        def __repr__(self):
            return (f'labelthread(#{self.id}: {self.label_list})'
                    if self.label_list is not None
                    else f'labelthread(#{self.id})')

        # AbstractOp

        def receive(self, env, x):
            self.send(env, self.label_tuple + x if type(x) is tuple else self.label_list + x)

        def receive_error(self, env, error):
            error.set_label(self.label_tuple[0])
            super().receive_error(env, error)

        # LabelThread internals

        @staticmethod
        def next_id():
            id = Remote.LabelThread.ID_COUNTER
            Remote.LabelThread.ID_COUNTER += 1
            return id

    class RunRemote(marcel.core.Op):

        def __init__(self, host, pipeline):
            super().__init__()
            self.host = host
            self.pipeline_wrapper = pipeline
            self.process = None

        def __repr__(self):
            return f'runremote({self.host}, {self.pipeline_wrapper})'

        # AbstractOp

        def run(self, env):
            # Start the remote process
            farcel_invocation = self.farcel_invocation()
            self.process = subprocess.Popen(farcel_invocation,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            shell=True,
                                            universal_newlines=False)
            buffer = io.BytesIO()
            pickler = dill.Pickler(buffer)
            try:
                pickler.dump(marcel.util.python_version())
                pickler.dump(env.marcel_usage())
                pickler.dump(self.pipeline_wrapper)
            except Exception as e:
                print(f'Caught ({type(e)} {e}', file=sys.stderr)
            buffer.seek(0)
            try:
                stdout, stderr = self.process.communicate(input=buffer.getvalue())
                stderr_lines = stderr.decode('utf-8').split('\n')
                if len(stderr_lines[-1]) == 0:
                    del stderr_lines[-1]
                sys.stdout.flush()
                for line in stderr_lines:
                    print(line, file=sys.stderr)
                sys.stderr.flush()
                input = dill.Unpickler(io.BytesIO(stdout))
                try:
                    while True:
                        x = input.load()
                        if isinstance(x, marcel.object.error.Error):
                            self.send_error(env, x)
                        else:
                            self.send(env, x)
                except EOFError as e:
                    self.propagate_flush(env)
            except BaseException as e:
                marcel.util.print_stack_of_current_exception()
                print(e)

        def farcel_invocation(self):
            cluster = self.host.cluster
            buffer = []
            if cluster.password:
                buffer.extend(['sshpass', '-p', f'"{cluster.password}"'])
            buffer.append('ssh')
            if cluster.identity:
                buffer.extend(['-i', cluster.identity])
            if self.host.port is not None:
                buffer.extend(['-p', str(self.host.port)])
            buffer.extend([f'{cluster.user}@{self.host.addr}', 'farcel.py'])
            return ' '.join(buffer)

        # Op

        def must_be_first_in_pipeline(self):
            return True

    def __init__(self):
        super().__init__()
        self.cluster = None
        self.pipeline_arg = None
        self.fork_manager = None

    def __repr__(self):
        return f'remote({self.cluster}, {self.pipeline_arg})'

    # AbstractOp

    def setup(self, env):
        self.fork_manager = marcel.op.forkmanager.ForkManager(op=self,
                                                              thread_ids=self.cluster.hosts,
                                                              pipeline_arg=self.pipeline_arg,
                                                              max_pipeline_args=0,
                                                              customize_pipeline=self.customize_pipeline)
        self.fork_manager.setup(env)

    # Op

    def run(self, env):
        self.fork_manager.run(env)

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def customize_pipeline(self, env, pipeline, host):
        remote = Remote.RunRemote(host, pipeline)
        label_thread = Remote.LabelThread(host)
        label_thread.receiver = self.receiver
        customized_pipeline = marcel.core.PipelineExecutable()
        customized_pipeline.params = pipeline.params
        customized_pipeline.append(remote)
        customized_pipeline.append(label_thread)
        return customized_pipeline
