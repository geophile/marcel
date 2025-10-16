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

import sys

import marcel.exception


class Platform(object):

    def remote_farcel_invocation(self):
        return 'farcel.py'

    @staticmethod
    def create():
        if sys.platform == 'linux':
            return PlatformLinux()
        elif sys.platform == 'darwin':
            return PlatformMacOS()
        else:
            raise marcel.exception.KillShellException(f'Unsupported platform: {sys.platform}')


class PlatformLinux(Platform):
    pass


class PlatformMacOS(Platform):

    def remote_farcel_invocation(self):
        return "'zsh -l -c farcel.py'"