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


class ForkManager(object):

    def __init__(self,
                 op,
                 thread_ids,
                 pipeline_arg,
                 max_pipeline_args=0,
                 customize_pipeline=lambda env, pipeline, thread_id: pipeline):
        self.op = op
        self.thread_ids = thread_ids
        self.customize_pipeline = customize_pipeline
        self.pipeline_arg = pipeline_arg
        self.max_pipeline_args = max_pipeline_args
        self.workers = []

    def __repr__(self):
        return f'forkmanager({self.thread_ids})'

    def setup(self, env):
        for thread_id in self.thread_ids:
            self.workers.append(ForkWorker(env, self, thread_id))

    def run(self, env):
        for worker in self.workers:
            worker.start_process()
        for worker in self.workers:
            worker.wait()


class ForkWorker(object):

    class SendToParent(marcel.core.Op):

        def __init__(self, parent):
            super().__init__()
            self.parent = parent

        def __repr__(self):
            return 'sendtoparent()'

        def receive(self, env, x):
            self.parent.send(dill.dumps(x))

        def receive_error(self, env, error):
            self.parent.send(dill.dumps(error))

    def __init__(self, env, fork_manager, thread_id):
        self.env = env
        self.fork_manager = fork_manager
        op = fork_manager.op
        self.thread_id = thread_id
        self.process = None
        # duplex=False: child writes to parent when function completes execution.
        # No need to communicate in the other direction
        self.reader, self.writer = mp.Pipe(duplex=False)
        self.pipeline = marcel.core.Pipeline.create(fork_manager.pipeline_arg, self.customize_pipeline)
        self.pipeline.setup(env)
        if self.pipeline.n_params() > fork_manager.max_pipeline_args:
            raise marcel.exception.KillCommandException('Too many pipelines args.')

    def start_process(self):
        def run_pipeline_in_child():
            try:
                self.pipeline.run_pipeline(self.env, [self.thread_id])
            except BaseException as e:
                self.writer.send(dill.dumps(e))
            self.writer.close()
        self.process = mp.Process(target=run_pipeline_in_child, args=tuple())
        self.process.daemon = True
        self.process.start()
        self.writer.close()

    def wait(self):
        try:
            op = self.fork_manager.op
            while True:
                input = self.reader.recv()
                x = dill.loads(input)
                op.send(self.env, x)
        except EOFError:
            pass
        while self.process.is_alive():
            self.process.join(0.1)
        self.env = None

    def customize_pipeline(self, env, pipeline):
        pipeline = self.fork_manager.customize_pipeline(env, pipeline, self.thread_id)
        send_to_parent = ForkWorker.SendToParent(self.writer)
        pipeline.append(send_to_parent)
        return pipeline
