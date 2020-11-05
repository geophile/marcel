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

import marcel.job
import marcel.op.jobop

job_control = marcel.job.JobControl.only


HELP = '''
{L}bg JOB

{L,indent=4:28}{r:JOB}                     The number of the job to be run in the background.

Resumes background execution of a suspended job. The {r:JOB} number is the one
provided by the {n:jobs} operator.
'''


class BgArgsValidator(marcel.op.jobop.JobOpArgsParser):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__('bg', env)


class Bg(marcel.op.jobop.JobOp):

    def __init__(self, env):
        """
        Initialize the environment.

        Args:
            self: (todo): write your description
            env: (todo): write your description
        """
        super().__init__(env)

    def __repr__(self):
        """
        Return a human - like object.

        Args:
            self: (todo): write your description
        """
        return f'bg(job={self.jid})' if self.jid is not None else f'bg(pid={self.pid})'

    # JobOp

    def action(self):
        """
        Run an action.

        Args:
            self: (todo): write your description
        """
        self.job.run_in_background()
