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
A marcel {i:command} is what you type following the prompt. A command may 
be a single marcel operator, or host OS executable, or it can combine several
of these via piping, (run {n:help pipeline} for more information on this topic). 
A single marcel command may span multiple lines, as long as a \\\\ is typed at the
end of each non-terminal line.
Marcel operators and host OS executables are distinguished as follows:

{L,indent=4:4}{i:Marcel operator:} A command that is built into marcel. In its most 
general form, an operator receives an input stream containing Python tuples,
and writes an output stream containing Python tuples. Every marcel operator
provides documentation via the {r:help}
command. For more information on operators in general, run {n:help operator}.

{L,indent=4:4}{i:Linux executable:} Linux executables can be executed, as with any other
shell. Many such executables can read and write streams of strings, which can
be carried by marcel pipes.

{b:Operators}

A marcel operator does one well-defined thing. For example, the {n:map} operator
applies a function to each tuple arriving on its input stream, and writes the result
to the output stream. {n:map} does not concern itself with printing these results -- that 
would be done by using the {n:out} operator later in the pipeline.

Many Linux commands have large collections of flags and options controlling the selection
and printing of relevant information. Marcel aims for simpler operators, and relies on
piping and general-purpose operators for selection and formatting. For example, the Linux
command {n:ls -rlt} does the following:

{L}- Lists the contents of the current directory.
{L}- {r:-l} prodcues detailed information for each file.
{L}- {r:-t} orders output by the file's modification time.
{L}- {r:-r} reverses the order so that the most recently modified files are listed last.

The marcel equivalent is:

{L,wrap=F}ls | sort (f: f.mtime)

{L}- {r:ls} lists the files in the current directory.
{L}- {r:sort (f: f.mtime)} sorts by file modification time.

Reversing is not necessary because sorting already orders from oldest to newest.
But if you wanted the opposite order you could either sort by {r:-f.mtime}, or:

{L,wrap=F}ls | sort (f: f.mtime) | reverse

The output from marcel is similar to that obtained by the Linux {r:ls} command
with the {r:-l} flag.

For more information on operators in general,
run {n:help operator}. 

The use of "ls" as the name of the marcel operator for listing files
needs some explaining: In some cases, the marcel operator has the same
name as a Linux executable with similar capabilities,
e.g. {n:ls}. This is intentional, as the Linux executable operates in
ways incompatible with marcel. (The Linux executable can still be
executed by using the {n:bash} command, e.g. {n:bash ls}.)

{b:Assignment}

Variables can be assigned in marcel as follows:

{L}HELLO = hello

(This is syntactic sugar for an invocation of the assignment
operator.)

This assigns the string {r:"hello"} to the variable
{r:HELLO}. Following this assignment, the variable {r:HELLO} is
present in the marcel namespace, as can be seen by running the {n:env}
command.

Note that the value of {r:hello} is of type str. Quoting would be
necessary for the usual reasons, e.g. if the string you want to assign
has whitespace in it.

You can also assign values of other types by evaluating a function 
computing a value of the correct type. E.g.

{L}THREE = (1 + 2)

{r:(1 + 2)} is a function which computes the integer 3, which is then assigned to 
the variable {r:THREE}. 

Run {n:help function} for more information on functions.

{b:Executables}

Executables can be run from marcel, just as in any other shell. stdout
and stderr from an executable can flow into a marcel pipeline, and will show up 
as a stream of strings, each terminated by \\\\n. Similarly, a marcel pipeline can
deliver data to an executable via stdin.

{b:Combining operators and executables}

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

{L}- {r:map (line: line.split(':'))}: Split the lines at the {n::} separators, yielding 7-tuples.

{L}- {r:select (*line: line[-1] == '/bin/bash')}: Select those lines in which the last field is 
{r:/bin/bash}.

{L}- {r:map (*line: line[0])}: Keep the username field of each input tuple.

{L}- {r:xargs echo}: Combine the incoming usernames into a single line, which is printed to {n:stdout}.

{L}- {r:\\\\}: A line terminating in {r:\\\\} indicates that the command continues on the next line.
'''
