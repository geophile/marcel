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
import marcel.job


HELP = '''
{L,wrap=F}jobs

Write the currently running jobs to the output stream. This includes jobs that are currently paused.

The jobs listed may be running, denoted as {n:(+)}; or paused, denoted as {n:(-)}.
While it is extremely unlikely, a job that is no longer running may be displayed
also, denoted as {n:(x)}. 
    
Every job includes a job number and a process id. Note that job numbers may change over time,
as a job number simply reflects the job's position in the list of jobs. Process ids never change.
The job number can be used in conjunction with the {r:bg} and {r:fg} commands.
'''


def jobs(env):
    return Jobs(env)


class JobsArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('jobs', env)
        self.validate()


class Jobs(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)

    def __repr__(self):
        return f'jobs'

    # AbstractOp
    
    def run(self):
        job_id = 0
        for job in marcel.job.JobControl.only.jobs():
            # TODO: If job were a marcel.object, then it would have render_compact/full methods.
            description = f'{job_id}({job.state_symbol()}): {job.process.pid}  {job.command.source}'
            self.send(description)
            job_id += 1

    # Op

    def run_in_main_process(self):
        return True
