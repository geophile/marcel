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

import marcel.core
import marcel.exception
import marcel.job


class JobOpArgParser(marcel.core.ArgParser):

    def __init__(self, op_name, env, summary, details):
        super().__init__(op_name, env, None, summary, details)
        id_group = self.add_mutually_exclusive_group()
        id_group.add_argument('-j', '--job',
                              type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                            'must be non-negative'),
                              dest='jid',
                              help='A job number, (not a process id)')
        id_group.add_argument('-p', '--process',
                              type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                            'must be non-negative'),
                              dest='pid',
                              help='A process id')
        self.add_argument('job_id',
                          nargs='?',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'),
                          help='A job number, (not a process id)')


class JobOp(marcel.core.Op):
    
    def __init__(self, env):
        super().__init__(env)
        self.jid = None
        self.pid = None
        self.job_id = None
        self.job = None

    # BaseOp

    def setup_1(self):
        job_control = marcel.job.JobControl.only
        if self.jid is None and self.pid is None and self.job_id is None:
            raise marcel.exception.KillCommandException(f'Must specify a job or process.')
        flag_specified = self.jid is not None or self.pid is not None
        if flag_specified and self.job_id is not None:
            raise marcel.exception.KillCommandException(f'Job/process identification specified more than once.')
        if self.job_id is not None:
            self.jid = self.job_id
        assert (self.jid is None) != (self.pid is None)
        if self.jid is not None and self.jid >= len(job_control.jobs()):
            raise marcel.exception.KillCommandException(f'There is no job {self.jid}')
        self.job = job_control.job(jid=self.jid, pid=self.pid)

    def receive(self, x):
        self.action()

    # Op

    def must_be_first_in_pipeline(self):
        return True

    def run_in_main_process(self):
        return True

    # JobOp

    def action(self):
        assert False
