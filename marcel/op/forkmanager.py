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

import multiprocessing as mp

import dill

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.cluster
import marcel.object.error
import marcel.util


def run_pipeline_in_child(env, pipeline, thread_id, writer):
    try:
        params = pipeline.parameters()
        bindings = {} if len(params) == 0 else {params[0]: thread_id}
        pipeline.run_pipeline(env, bindings)
    except BaseException as e:
        marcel.util.print_stack_of_current_exception()
        writer.send(dill.dumps(e))
    writer.close()


class ForkManager(object):

    def __init__(self,
                 op,
                 thread_ids,
                 pipeline,
                 max_pipeline_args=0):
        if len(pipeline.parameters()) > max_pipeline_args:
            raise marcel.exception.KillCommandException('Too many pipeline args.')
        self.op = op
        self.thread_ids = thread_ids
        self.pipeline = pipeline
        self.max_pipeline_args = max_pipeline_args
        self.workers = None

    def __repr__(self):
        return f'forkmanager({self.thread_ids})'

    def setup(self, env, customize_pipeline=None):
        self.workers = [ForkWorker(env, self, thread_id, customize_pipeline) for thread_id in self.thread_ids]

    def run(self, env):
        for worker in self.workers:
            worker.start_process()
        for worker in self.workers:
            worker.wait()

class ForkWorker(object):

    class SendToParent(marcel.core.Op):

        def __init__(self, writer):
            super().__init__()
            self.writer = writer

        def __repr__(self):
            return 'sendtoparent()'

        def receive(self, env, x):
            self.writer.send(dill.dumps(x))

        def receive_error(self, env, error):
            self.writer.send(dill.dumps(error))

    def __init__(self, env, fork_manager, thread_id, customize_pipeline):
        self.env = env
        self.op = fork_manager.op
        self.pipeline = (customize_pipeline(env, fork_manager.pipeline, thread_id)
                         if customize_pipeline else
                         fork_manager.pipeline)
        self.thread_id = thread_id
        self.process = None
        # duplex=False: child writes to parent when function completes execution.
        # No need to communicate in the other direction
        self.reader, self.writer = mp.Pipe(duplex=False)

    def start_process(self):
        # Extending pipeline, as Ops do in customize_pipelines
        send_to_parent = ForkWorker.SendToParent(self.writer)
        self.pipeline = self.pipeline.append_immutable(send_to_parent)
        #
        self.process = mp.Process(target=run_pipeline_in_child,
                                  args=(self.env, self.pipeline, self.thread_id, self.writer))
        self.process.daemon = True
        #
        # from marcel.util import PickleDebugger
        # import sys
        # PickleDebugger().check(self.pipeline)
        # sys.exit(123)
        #
        self.process.start()
        self.writer.close()

    def wait(self):
        try:
            while True:
                input = self.reader.recv()
                x = dill.loads(input)
                self.op.send(self.env, x)
        except EOFError:
            pass
        while self.process.is_alive():
            self.process.join(0.1)
        self.env = None
