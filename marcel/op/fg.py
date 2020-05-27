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

import marcel.op.jobop


SUMMARY = '''
Make a specified background job run in the foreground. 
'''


DETAILS = '''
The new foreground job is resumed if necessary.
'''


class FgArgsValidator(marcel.op.jobop.JobOpArgsParser):

    def __init__(self, env):
        super().__init__('fg', env)


class Fg(marcel.op.jobop.JobOp):

    def __init__(self, env):
        super().__init__(env)

    def __repr__(self):
        return f'fg(job={self.jid})' if self.jid is not None else f'fg(pid={self.pid})'

    # JobOp

    def action(self):
        self.job.run_in_foreground()
