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

import marcel.exception

VERSION = '0.24.1'


def _kill_shell(message):
    raise marcel.exception.KillShellException(message)


def major_minor(version=VERSION):
    if type(version) is not str:
        _kill_shell(f'Version number not a string: {version}')
    version_parts = version.split('.')
    if len(version_parts) != 3:
        _kill_shell(f'Incorrectly formatted version number: {version}')
    for part in version_parts:
        if not part.isdigit():
            _kill_shell(f'Invalid version number: {version}')
    return '.'.join(version_parts[:2])
