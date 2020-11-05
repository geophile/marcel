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

import psutil

proc_attrs = ['cmdline',
              'cpu_percent',
              'cpu_times',
              'create_time',
              'cwd',
              'environ',
              'exe',
              'gids',
              'memory_info',
              'name',
              'pid',
              'ppid',
              'username',
              'uids']
for p in psutil.process_iter(proc_attrs):
    print(p.pid)
    for k, v in p.info.items():
        print(f'    {k}: {v}')
