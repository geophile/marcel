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
A marcel {i:command} is a single action entered on the command line. There are
two types of commands:

{L,indent=4:4}{i:Marcel operator:} A command that is built into marcel. In its most 
      general form, an operator receives an input stream containing Python tuples,
      and writes an output stream containing Python tuples. Every marcel operator
      provides documentation via the help flags ({r:-h}, {r:--help}), or the {r:help}
      command. For more information on operators, run {n:help operator}.

{L,indent=4:4}{i:Linux executable:} Linux executables can be executed, as with any other
      shell. Many such executables can read and write streams of strings.

In some cases, the marcel operator has the same name as a Linux
executable with similar capabilities, e.g. {n:ls}. This is intentional,
as the Linux executable operates in ways incompatible with
marcel. (The Linux executable can still be executed by using the
{n:bash} command, e.g. {n:bash ls}.)

Operators and executables can be mixed freely. For example, here is a
command sequence that lists the names of users whose shell is
{n:/bin/bash}. 
{p,wrap=F}
    cat /etc/passwd | \\\\
    map (line: line.split(':')) | \\\\
    select (*line: line[-1] == '/bin/bash') | \\\\
    map (*line: line[0]) | \\\\
    xargs echo

The file {n:/etc/passwd} contains usernames and shell
executables. This file is written to {n:stdout} by using
the Linux executable {n:cat}. {n:stdout} then feeds into a sequence of
three marcel operators ({r:map}, {r:select}, and then {r:map} again), and the
output from these operators feeds into another Linux executable, {r:xargs}, which
uses invokes {r:echo}.

Comments:

{L}- {r:cat /etc/passwd}: Write each line of {r:/etc/passwd} to the output stream.

{L}- {r:map (line: line.split(':'))}: Split the lines at the {n:} separators, yielding 7-tuples.

{L}- {r:select (*line: line[-1] == '/bin/bash')}: Select those lines in which the last field is 
{r:/bin/bash}.

{L}- {r:map (*line: line[0])}: Keep the username field of each input tuple.

{L}- {r:xargs echo}: Combine the incoming usernames into a single line, which is printed to {n:stdout}.

{L}- {r:\\\\}: A line terminating in {r:\\\\} indicates that the command continues on the next line.
'''
