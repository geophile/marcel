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
import marcel.op.forkmanager
import marcel.util

HELP = '''
{L,wrap=F}fork FORK_GEN PIPELINE

{L,indent=4:28}{r:FORK_GEN}                An int or iterable used to generate forks.
   
{L,indent=4:28}{r:PIPELINE}                A pipeline whose instances are to be executed concurrently.

Instances of a pipeline are executed concurrently.

{r:FORK_GEN} is an int or an iterable, used to specify the number of
concurrent executions of {r:PIPELINE}. For discussion purposes, the
execution of each instance of {r:PIPELINE} is executed by a thread, but
the actual implementation is unspecified. {r:PIPELINE} has no arguments, or
one argument, a
thread id. Output from {r:fork} comprises tuples containing the thread id,
and the output from the pipeline instance.

If {r:FORK_GEN} is an int, N, then the thread ids are 0, ..., N-1.

If {r:FORK_GEN} is an iterable, then the thread ids are the values obtained by iteration, 
(i.e., successive calls to next()).

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

{r:FORK_GEN} may be a {n:Cluster}, because {n:Cluster} is iterable.
In this case, the thread ids are the {n:Host} objects comprising the named cluster.
But it should not normally be necessary to use a {n:Cluster} in this way. Instead, consider
using the {n:upload} or {n:download} operators, or remote execution syntax, e.g.

{p,indent=4}
@my_cluster [ps] 
'''


def fork(env, forkgen, pipeline):
    # callable: Through API.
    # not callable: Interactive.
    pipeline_arg = marcel.core.PipelineFunction(pipeline) if callable(pipeline) else pipeline
    return Fork(env), [forkgen, pipeline_arg]


# For API
class ForkArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('fork', env)
        self.add_anon('forkgen', convert=self.fork_gen)
        self.add_anon('pipeline', convert=self.check_str_or_pipeline, target='pipeline_arg')
        self.validate()


class Fork(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.forkgen = None
        self.thread_ids = None
        self.pipeline_arg = None
        self.manager = None
        self.workers = None

    def __repr__(self):
        return f'fork({self.forkgen}, {self.pipeline_arg})'

    # AbstractOp

    def setup(self):
        pipeline_arg = self.pipeline_arg
        assert isinstance(pipeline_arg, marcel.core.Pipelineable)
        forkgen = self.eval_function('forkgen') if callable(self.forkgen) else self.forkgen
        if type(forkgen) is int:
            if forkgen > 0:
                self.thread_ids = list(range(forkgen))
            else:
                raise marcel.exception.KillCommandException(f'Int fork generator must be positive.')
        elif marcel.util.iterable(forkgen):
            self.thread_ids = list(forkgen)
            if len(self.thread_ids) == 0:
                raise marcel.exception.KillCommandException(f'Iterable fork generator must not be empty.')
        else:
            raise marcel.exception.KillCommandException(f'Invalid fork generator.')
        self.manager = marcel.op.forkmanager.ForkManager(op=self,
                                                         thread_ids=self.thread_ids,
                                                         pipeline_arg=pipeline_arg,
                                                         max_pipeline_args=1)
        self.manager.setup()

    # Op

    def run(self):
        self.manager.run()

    def must_be_first_in_pipeline(self):
        return True
