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
This information is derived from the {n:proc} filesystem. E.g., the
directory {n:/proc/23419} has files with information on the process whose
pid is 23419.

There are about 50 files in the {n:/proc} directory for a
process. Marcel uses three of them:

{L}{n:status}: Contains information on resource usage,
ownership, process state, and much else.

{L}{n:commandline}: The commandline used to launch the 
process (if the process was launched that way).

{L}{n:environ}: The environment variables for the process.

{b:Process properties}

A {n:Process} has the following properties:

{L,indent=4:6}- {n:pid}: The pid of the process.
{L,indent=4:6}- {n:ppid}: The pid of the parent of the process.     
{L,indent=4:6}- {n:uid}: The effective uid of the process.
{L,indent=4:6}- {n:user}: The username of the effective uid.
{L,indent=4:6}- {n:gid}: The effective gid of the process.
{L,indent=4:6}- {n:group}: The group name of the effective gid.
{L,indent=4:6}- {n:state}: The execution state of the process.
{L,indent=4:6}- {n:commandline}: The command line used to launch the process.
{L,indent=4:6}- {n:env}: The environment variables of the process.

These properties represent information derived from the {n:status},
{n:cmdline}, and {n:environ} files, modified in some cases for convenience.
For example, all of the numbers are converted to {n:int}.

The contents of the {n:status} file can also be accessed directly, by
using the key from that file. So, for example, there is a {n:Uid}
property, whose value is a string containing four uids. (The second of
these is extracted as the value of the {n:uid} property).


{b:Process functions}

A signal can be sent to a process by using the {n:signal} function. For example,
to attempt to kill all processes owned by user "djt":

{p,wrap=F,indent=4}
ps | select (p: p.user == 'djt') | map (p: p.signal(9))
'''
