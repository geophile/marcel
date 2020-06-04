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
A {i:pipeline} is a sequence of commands connected by pipes.
Every marcel command amounts to the execution of a pipeline.

{b:A pipeline can be an argument to an operator}

A pipeline can also appear as an argument for some operators.
In the case, the pipeline is bracketed: using {n:[...]} 
For example, this pipeline lists the sum of file sizes under 
{n:/tmp}:

{p,wrap=F}
    ls -fr /tmp | map (f: f.size) | red +

To run this command on a remote host named {n:fred}:

{p,wrap=F}
    @fred [ ls -fr /tmp | map (f: f.size) | red + ]

Comments:

{L}- {r:@fred}: The name {r:fred} has been configured to refer to some host, and to 
provide login credentials.
{L}- {r:[...]}: The pipeline to be executed on {r:fred} is delimited by {r:[...]}
{L}- The output includes the name of the host on which the command executed, e.g.
{n:(fred, 1366422)}

The summation could also done locally, by returning the file sizes, and
then doing the summation:

{p,wrap=F}
    @fred [ ls -fr /tmp ] | map (host, file: file.size) | red +

Comments:

{L}- The remote command returns (host, {n:File}) tuples.
{L}- {r:map (host, file: file.size)}: This function discards the host information, 
      and extracts the size of the {n:File}. (The file's size was captured remotely 
      and returned with the {n:File} object.)

{b:A pipeline can be used to define a new operator}

A pipelines can also be assigned to a variable, essentially creating a
new operator. For example, this command assigns a pipeline to the {r:recent}
variable:

{L,wrap=F}recent = [select (file: now() - file.mtime < days(1))]

Explanation:

{L}- {r:select(file: ...)} The pipeline uses one operator, {r:select}, to take
{n:File}s as input, and keep those that have been changed in the past day.
{L}- {r:now()} is a function provided by marcel, which simply runs {n:time.time()}. I.e.,
it returns the number of seconds since the epoch.
{L}- {r:file.mtime}: {n:File} defines the {n:mtime} property, which is the time of the
{n:File}s last modification.
{L}- {r:days(1)} returns the number of seconds in 1 day.

In other words, this pipeline expects {n:File}s to be piped in, and it keeps those
that have been modified in the past day. This can be used with any source of {n:File}s, 
e.g.

{L,wrap=F}ls -fr | recent

This command lists all files inside the current directory,
recursively, and prints out those that changed within the past day.
'''
