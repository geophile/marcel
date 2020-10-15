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
import marcel.job


class JobOpArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, op_name, env):
        super().__init__(op_name, env)
        self.add_flag_one_value('jid', '-j', '--job', convert=self.str_to_int)
        self.add_flag_one_value('pid', '-p', '--process', convert=self.str_to_int)
        self.add_anon('job_id', convert=self.str_to_int)
        self.exactly_one('jid', 'pid', 'job_id')
        self.validate()


class JobOp(marcel.core.Op):
    
    def __init__(self, env):
        super().__init__(env)
        self.jid = None
        self.pid = None
        self.job_id = None
        self.job = None

    # AbstractOp

    def setup(self):
        job_control = marcel.job.JobControl.only
        if self.job_id is not None:
            self.jid = self.job_id
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
