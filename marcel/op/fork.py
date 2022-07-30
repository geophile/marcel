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
import subprocess
import io
import sys

import dill

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.object.cluster
import marcel.object.error
import marcel.util

HELP = '''
{L,wrap=F}fork FORK_GEN PIPELINE

{L,indent=4:28}{r:FORK_GEN}                An int or iterable used to generate forks.
   
{L,indent=4:28}{r:PIPELINE}                A pipeline whose instances are to be executed concurrently.

Instances of a pipeline are executed concurrently.

{r:FORK_GEN} is an int or an iterable, used to specify the number of
concurrent executions of {r:PIPELINE}. For discussion purposes, the
execution of each instance of {r:PIPELINE} is executed by a thread, but
the actual implementation is unspecified. {r:PIPELINE} has one argument, a
thread id. Output from {r:fork} comprises tuples containing the thread id,
and the output from the pipeline instance.

Example:

{p,indent=4,wrap=F}
fork 3 [id: gen (id+1) 100]

This command creates three threads, with ids 0, 1, 2. For id 0, the
command executed is gen 1 100, which generates the stream [100]. For
id 1, the stream is [100, 101], and for id 2, the stream is [100, 101,
102]. The fork command prepends the id to each tuple of output from
the gen operator, so the output for the command is something like
this:

{p,indent=4,wrap=F}
(0, 100)
(1, 100)
(2, 100)
(1, 101)
(2, 101)
(2, 102)

(Any interleaving of the streams may be observed.)

If {r:FORK_GEN} is an iterable, then the thread id is bound to each value
returned by the iterable. So this command:

{p,indent=4,wrap=F}
fork 'abc' [id: gen 3 100]

yields:

{p,indent=4,wrap=F}
('a', 100)
('b', 100)
('c', 100)
('a', 101)
('b', 101)
('c', 101)
('a', 102)
('b', 102)
('c', 102)

{r:FORK_GEN} may be a {n:Cluster}. A {n:Cluster} is iterable, and the values
obtained by iteration are {n:Host} objects.

It should not normally be necessary to use a {n:Cluster} for
{r:FORK_GEN}. Remote execution can be done by using special syntax,
e.g. to send a {n:grep} command to each node in cluster {r:lab}:

{p,indent=4,wrap=F}
@lab [grep foobar /var/log/syslog]

This is equivalent to:

{p,indent=4,wrap=F}
fork lab [host: ssh -i ~/.ssh/(host).pem -l (host.cluster.user) (host) "grep foobar /var/log/syslog"]

Similarly, copying files to and from clusters can be done using the
{r:fork} command (e.g., with the {r:PIPELINE} using {n:rsync}), but it would be
far simpler to use the {n:upload} and {n:download} commands.
'''


def fork(env, forkgen, pipelineable):
    assert isinstance(pipelineable, marcel.core.Pipelineable)
    pipelineable = pipelineable.create_pipeline()
    return Fork(env), [forkgen, pipelineable]


# For API
def fork_remote(env, forkgen, pipelineable):
    assert isinstance(pipelineable, marcel.core.Pipelineable)
    pipelineable = pipelineable.create_pipeline()
    fork = Fork(env)
    fork.execute_remotely()
    return fork, [forkgen, pipelineable]


class ForkArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('fork', env)
        self.add_anon('forkgen', convert=self.fork_gen)
        self.add_anon('pipeline', convert=self.check_pipeline)
        self.validate()


class Fork(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.forkgen = None
        self.pipeline = None
        self.impl = None
        self.workers = None
        self.remote = False

    def __repr__(self):
        op_name = 'remote' if self.remote else 'fork'
        return f'{op_name}({self.forkgen}, {self.pipeline})'

    # AbstractOp

    def setup(self):
        params = self.pipeline.params
        if params and len(params) > 1:
            raise marcel.exception.KillCommandException('fork pipeline must have no more than one parameter.')
        forkgen = self.eval_function('forkgen') if callable(self.forkgen) else self.forkgen
        if type(forkgen) is int:
            self.impl = ForkInt(self, forkgen)
        elif self.remote:
            self.impl = ForkRemote(self, forkgen)
        elif marcel.util.iterable(forkgen):
            self.impl = ForkIterable(self, forkgen)
        else:
            raise marcel.exception.KillCommandException(f'fork generator must be an int, Cluster, or iterable.')
        self.workers = []
        for thread_id in self.impl.thread_ids:
            self.workers.append(ForkWorker(self, thread_id))

    # Op

    def run(self):
        for worker in self.workers:
            worker.start_process()
        for worker in self.workers:
            worker.wait()

    def must_be_first_in_pipeline(self):
        return True

    # Fork

    def execute_remotely(self):
        self.remote = True


class ForkWorker:

    def __init__(self, op, thread_id):
        self.op = op
        self.thread_id = thread_id
        self.process = None
        # duplex=False: child writes to parent when function completes execution. No need to communicate in the
        # other direction
        self.reader, self.writer = mp.Pipe(duplex=False)
        self.pipeline = op.impl.pipeline_instance(self)

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


class ForkImpl(object):

    class LabelThread(marcel.core.Op):

        ID_COUNTER = 0

        def __init__(self, env, label):
            super().__init__(env)
            self.label_list = [label]
            self.label_tuple = (label,)
            self.id = ForkImpl.LabelThread.ID_COUNTER
            ForkImpl.LabelThread.ID_COUNTER += 1

        def __repr__(self):
            return (f'labelthread(#{self.id}: {self.label_list})'
                    if self.label_list is not None
                    else f'labelthread(#{self.id})')

        # AbstractOp

        def receive(self, x):
            self.send(self.label_tuple + x
                      if type(x) is tuple
                      else self.label_list + x)

        def receive_error(self, error):
            error.set_label(self.label_tuple[0])
            super().receive_error(error)

    def __init__(self, op):
        self.op = op
        self.thread_ids = None

    def pipeline_instance(self, fork_worker):
        # Copy the op's pipeline
        op = self.op
        pipeline = op.pipeline.copy()
        pipeline.set_error_handler(op.pipeline.error_handler)
        return pipeline


class ForkRemote(ForkImpl):

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

    class Remote(marcel.core.Op):

        def __init__(self, env, host, pipeline):
            super().__init__(env)
            self.host = host
            self.pipeline = pipeline
            self.process = None

        def __repr__(self):
            return f'remote({self.host}, {self.pipeline})'

        # AbstractOp

        def setup(self):
            pass

        def run(self):
            # Start the remote process
            command = ' '.join([
                'ssh',
                '-l',
                self.host.user,
                '-i',
                self.host.cluster.identity,
                self.host.addr,
                'farcel.py'
            ])
            self.process = subprocess.Popen(command,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            shell=True,
                                            universal_newlines=False)
            buffer = io.BytesIO()
            pickler = dill.Pickler(buffer)
            pickler.dump(self.env().python_version())
            pickler.dump(self.env().without_reservoirs())
            pickler.dump(self.pipeline)
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
                            self.send_error(x)
                        else:
                            self.send(x)
                except EOFError as e:
                    self.propagate_flush()
            except BaseException as e:
                marcel.util.print_stack()
                print(e)

        # Op

        def must_be_first_in_pipeline(self):
            return True

    def __init__(self, op, cluster):
        super().__init__(op)
        assert type(cluster) is marcel.object.cluster.Cluster
        self.cluster = cluster
        self.thread_ids = self.cluster.hosts

    def pipeline_instance(self, fork_worker):
        # Create a pipeline that:
        #    - Runs the op's pipeline remotely
        #    - Prepends the host to each tuple from the remote host
        #    - Sends tuples to the parent
        pipeline = marcel.core.Pipeline()
        op = self.op
        host = fork_worker.thread_id
        remote = ForkRemote.Remote(op.env(), host, op.pipeline)
        label_thread = ForkImpl.LabelThread(op.env(), host)
        send_to_parent = ForkRemote.SendToParent(op.env(), fork_worker.writer)
        pipeline.append(remote)
        pipeline.append(label_thread)
        pipeline.append(send_to_parent)
        label_thread.receiver = op.receiver
        return pipeline


class ForkInt(ForkImpl):

    def __init__(self, op, n_forks):
        super().__init__(op)
        if n_forks > 0:
            self.thread_ids = list(range(n_forks))
        else:
            raise marcel.exception.KillCommandException(f'If fork generator is an int, it must be positive.')


class ForkIterable(ForkImpl):

    def __init__(self, op, iterable):
        super().__init__(op)
        self.thread_ids = iterable
