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

import multiprocessing as mp

import dill

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.opmodule
import marcel.op.labelthread


def fork(env, host, pipelineable):
    assert isinstance(pipelineable, marcel.core.Pipelineable)
    pipelineable = pipelineable.create_pipeline()
    return Fork(env), [host, pipelineable]


class ForkArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('fork', env)
        self.add_anon('cluster', convert=self.fork_spec, target='cluster_name')
        self.add_anon('pipeline', convert=self.check_pipeline)
        self.validate()


class Fork(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.cluster_name = None
        self.cluster = None
        self.pipeline = None
        self.remote_pipeline = None
        self.workers = None

    def __repr__(self):
        return f'@{self.cluster_name} {self.pipeline}'

    # AbstractOp

    def setup(self):
        self.cluster = self.env().cluster(self.cluster_name)
        if self.cluster is None:
            raise marcel.exception.KillCommandException(f'There is no cluster named {self.cluster_name}')
        self.workers = []
        for host in self.cluster.hosts:
            self.workers.append(ForkWorker(host, self))

    # Op

    def run(self):
        for worker in self.workers:
            worker.start_process()
        for worker in self.workers:
            worker.wait()

    def must_be_first_in_pipeline(self):
        return True

    # Fork

    @staticmethod
    def return_remote_output(writer):
        def f(x):
            writer.send(dill.dumps(x))
        return f


class ForkWorker:

    class SendToParent(marcel.core.Op):

        def __init__(self, env, parent):
            super().__init__(env)
            self.parent = parent

        def __repr__(self):
            return 'sendtoparent()'

        def receive(self, x):
            self.parent.send(dill.dumps(x))

        def receive_error(self, error):
            self.parent.send(dill.dumps(error))

    def __init__(self, host, op):
        self.host = host
        self.op = op
        self.process = None
        # duplex=False: child writes to parent when function completes execution. No need to communicate in the
        # other direction
        self.reader, self.writer = mp.Pipe(duplex=False)
        self.pipeline = marcel.core.Pipeline()
        remote = marcel.opmodule.create_op(op.env(), 'remote', op.pipeline)
        remote.set_host(host)
        label_thread = marcel.op.labelthread.LabelThread(op.env())
        label_thread.set_label(host)
        send_to_parent = ForkWorker.SendToParent(self.op.env(), self.writer)
        self.pipeline.append(remote)
        self.pipeline.append(label_thread)
        self.pipeline.append(send_to_parent)
        label_thread.receiver = op.receiver

    def start_process(self):
        def run_pipeline_in_child():
            try:
                self.pipeline.set_error_handler(self.op.owner.error_handler)
                self.pipeline.setup()
                self.pipeline.set_env(self.op.env())
                self.pipeline.run()
                self.pipeline.flush()
                self.pipeline.cleanup()
            except BaseException as e:
                self.writer.send(dill.dumps(e))
            self.writer.close()
        self.process = mp.Process(target=run_pipeline_in_child, args=tuple())
        self.process.daemon = True
        self.process.start()
        self.writer.close()

    def wait(self):
        try:
            while True:
                input = self.reader.recv()
                x = dill.loads(input)
                self.op.send(x)
        except EOFError:
            pass
        while self.process.is_alive():
            self.process.join(0.1)
