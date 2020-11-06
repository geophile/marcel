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

HELP = ''' 

A {i:Process} represents an operating system process.  Marcel's {n:ps}
command generates a stream of {n:Process}es. {n:Process} provides a
set of properties and functions for obtaining information on processes.

{b:Process properties}

A {n:Process} is based on an object of the same name from the
{n:psutil} module. The properties of {n:Process} derived from {n:pustil}
are:

{L, indent=4:6}- {n:cmdline}
{L, indent=4:6}- {n:cpu_percent}
{L, indent=4:6}- {n:cpu_times}
{L, indent=4:6}- {n:create_time}
{L, indent=4:6}- {n:cwd}
{L, indent=4:6}- {n:environ}
{L, indent=4:6}- {n:exe}
{L, indent=4:6}- {n:gids}
{L, indent=4:6}- {n:memory_info}
{L, indent=4:6}- {n:name}
{L, indent=4:6}- {n:pid}
{L, indent=4:6}- {n:ppid}
{L, indent=4:6}- {n:status}
{L, indent=4:6}- {n:username}
{L, indent=4:6}- {n:uids}

Consult {n:psutil} documentation for information on these properties. In addition, the {n:command}
property returns the process command line as a single string, ({n:cmdline} returns a list of strings).

{b:Process methods}

A signal can be sent to a process by using the {n:signal} function. For example,
to attempt to kill all processes owned by user "djt":

{p,wrap=F,indent=4}
ps -u djt | map (p: p.signal(9))
'''
