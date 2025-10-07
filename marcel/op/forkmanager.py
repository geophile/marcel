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
import os

import dill

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.cluster
import marcel.object.error
import marcel.util


DUMP = False

def dump(message):
    if DUMP:
        print(f'{os.getpid()}: {message}')


def run_pipeline_in_child(env, pipeline, thread_id, writer):
    try:
        params = pipeline.parameters()
        bindings = {} if len(params) == 0 else {params[0]: thread_id}
        dump(f'child running pipeline {pipeline}, writer {id(writer)}')
        pipeline.run_pipeline(env, bindings)  # Closes writer
    except BaseException as e:
        dump(f'caught {type(e)}: {e}')
        marcel.util.print_stack_of_current_exception()
        writer.send(dill.dumps(e))
        writer.close()
    finally:
        dump(f'closed writer {id(writer)}')


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
        return f'ForkManager({self.thread_ids})'

    def setup(self, env, fork_customizer=None):
        self.workers = [ForkWorker(env, self, thread_id, fork_customizer) for thread_id in self.thread_ids]

    def run(self, env):
        for worker in self.workers:
            worker.start()
            dump(f'{self} started {worker}')
        completed = 0
        w = 0
        while completed < len(self.workers):
            more = self.workers[w].consume_input()
            if not more:
                completed += 1
            w = (w + 1) % len(self.workers)
            dump(f'completed: {completed}')
        for worker in self.workers:
            worker.close()

class ForkWorker(object):

    class SendToParent(marcel.core.Op):

        def __init__(self, writer, thread_id):
            super().__init__()
            self.writer = writer
            self.thread_id = thread_id
            dump(f'{self} init')

        def __repr__(self):
            return f'sendtoparent({self.thread_id})'

        def receive(self, env, x):
            dump(f'{self} receive {x}')
            self.writer.send(dill.dumps(x))
            dump(f'{self} receive sent {x}')

        def receive_error(self, env, error):
            dump(f'{self} receive_error {error}')
            self.writer.send(dill.dumps(error))

        def cleanup(self):
            dump(f'{self} cleanup, close writer {id(self.writer)}')
            self.writer.close()

    def __init__(self, env, fork_manager, thread_id, fork_customizer):
        self.env = env
        self.op = fork_manager.op
        self.pipeline = (fork_customizer(env, fork_manager.pipeline, thread_id)
                         if fork_customizer else
                         fork_manager.pipeline)
        self.pipeline = self.pipeline.copy()
        self.thread_id = thread_id
        self.process = None
        # duplex=False: child writes to parent when function completes execution.
        # No need to communicate in the other direction
        self.reader, self.writer = mp.Pipe(duplex=False)
        # Extending pipeline, as Ops do in customize_pipelines
        send_to_parent = ForkWorker.SendToParent(self.writer, self.thread_id)
        self.pipeline = self.pipeline.append_immutable(send_to_parent)
        dump(f'{self} init {self.pipeline}')

    def __repr__(self):
        return f'ForkWorker({self.thread_id})'

    def start(self):
        dump(f'{self} start_process {self.pipeline}')
        self.process = mp.Process(target=run_pipeline_in_child,
                                  args=(self.env, self.pipeline, self.thread_id, self.writer))
        dump(f'{self} created {self.process}')
        self.process.daemon = True
        #
        # from marcel.util import PickleDebugger
        # import sys
        # PickleDebugger().check(self.pipeline)
        # sys.exit(123)
        #
        self.process.start()
        # If multiprocessing operates using the fork model, then a file descriptor isn't closed
        # until both ends are closed.
        # https://stackoverflow.com/questions/6564395/why-doesnt-pipe-close-cause-eoferror-during-pipe-recv-in-python-multiproces
        self.writer.close()

    def consume_input(self):
        more = True
        try:
            if self.reader.poll(timeout=0.1):
                input = self.reader.recv()
                x = dill.loads(input)
                dump(f'{self} consume_input receive {x}')
                self.op.send(self.env, x)
        except EOFError:
            dump(f'{self} consume_input EOF')
            self.writer.close()
            more = False
        return more

    def close(self):
        dump(f'{self} joining ...')
        first = True
        while first or self.process.is_alive():
            dump(f'alive: {self.process.is_alive()}')
            self.process.join(0.1)
            first = False
        dump(f'{self} joined')
        self.env = None
