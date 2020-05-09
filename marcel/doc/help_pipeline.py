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
A {i:pipeline} is a sequence of commands combined by pipes.
A pipeline is bracketed using {n:[...]} when the pipeline is
part of another command. For example, this pipeline lists the sum of file sizes under 
{n:/tmp}:

{p,wrap=F}
    ls -fr /tmp | map (f: f.size) | red +

To run this command on a remote host named {n:fred}:

{p,wrap=F}
    @fred [ ls -fr /tmp | map (f: f.size) | red + ]

Comments:

{L}- {r:@fred}: The name {r:fred} has been configured to refer to some host, and to 
   provide login credentials. (For more information on configuration, run
   {n:help configuration}.)
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
'''
