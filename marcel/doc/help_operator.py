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
Marcel {i:operators} are built in commands, able to pass Python objects
to one another via pipes.

{b:Command-line arguments:}

In general, an operator has a number of command-line arguments,
comprising optional and positional arguments.

For example, the {n:timer} command has two optional arguments:

{p,indent=4}1) {r:-c} or equivalently {r:--components}, for controlling the behavior
of the operator.

{p,indent=4}2) {r:-h} or equivalently {r:--help} for obtaining documentation on the
operator. (All operators have these flags.)

{n:timer} also has one positional argument, {r:interval}. You can see
these described by running {n:timer -h}.

{b:Input and output streams:}

An operator may receive input from a preceding command through a pipe, and
send output to a succeeding operator through a pipe. The {n:timer} command
does not require an input stream, but it does generate output. For example,
{n:timer 1} generates a timestamp (seconds since the epoch), once every second.

Streams always carry tuples between commands. Often, these are
1-tuples.  For example, the {n:ls} operator generates a stream
containing {n:File} objects, each wrapped in a 1-tuple. When a Linux
executable is run, its {n:stdout} is conveyed to the next command by
wrapping strings (separated by \\\\n characters) in 1-tuples. Marcel
operators can generate n-tuples, with n > 1. For example, this command
sequence lists files (only, no directories or symlinks) in the current
directory, and uses the {r:map} operator to generate a stream of
filename and file size values:

{p,wrap=F,indent=4}ls -f | map (f: (f.name, f.size))

{b:Obtaining output}

The only marcel operator that writes output is {n:out}. Every command sequence
has an {n:out} at the end, implicitly if necessary. By default, {n:out} simply uses
the Python {n:str} method to generate its output. For example, the above command 
sequence generates output that looks like this (for {n:/etc/sysctl.d}):

{p,wrap=F,indent=4}
('10-console-messages.conf', 77)
('10-ipv6-privacy.conf', 490)
('10-kernel-hardening.conf', 726)
('10-link-restrictions.conf', 257)
('10-magic-sysrq.conf', 1184)
('10-network-security.conf', 158)
('10-pop-default-settings.conf', 19)
('10-ptrace.conf', 1292)
('10-zeropage.conf', 506)
('30-postgresql-shm.conf', 462)
('README.sysctl', 792)
('protect-links.conf', 324)

The {n:out} command can be made explicit to add formatting and redirection options.
For example, to format the above output differently:

{p,wrap=F,indent=4}
ls -f | map (f: (f.name, f.size)) | out '\{\}: \{\}'

The standard Python formatting string, '\{\}: \{\}' produces this output:

{p,wrap=F,indent=4}
10-console-messages.conf: 77
10-ipv6-privacy.conf: 490
10-kernel-hardening.conf: 726
10-link-restrictions.conf: 257
10-magic-sysrq.conf: 1184
10-network-security.conf: 158
10-pop-default-settings.conf: 19
10-ptrace.conf: 1292
10-zeropage.conf: 506
30-postgresql-shm.conf: 462
README.sysctl: 792
protect-links.conf: 324

Run {n:help out} for more information on the {n:out} command.

{b:Error handling}

In a major departure from other shells, marcel does not support the
concept of {n:stdout} and {n:stderr}. Instead, errors are written to the
operator's output stream as an object of type
{n:marcel.object.Error}. {n:Error}s are not passed through operators. Instead
they are forwarded from one stream to the next, until an {n:out} operator is encountered.
At that point, the {n:Error} is printed and then not passed further downstream.

For example, suppose directory {n:/tmp/d} contains three directories:

{p,wrap=F,indent=4}
M jao@cheese:/tmp/d$ ls
rwxr-xr-x jao      jao              4096 /tmp/d/hi
r-------- root     root             4096 /tmp/d/nope
rwxr-xr-x jao      jao              4096 /tmp/d/welcome

The {r:nope} directory cannot be visited, due to permissions. If we try
to list all files and directories recursively:

{p,wrap=F,indent=4}
M jao@cheese:/tmp/d$ ls -r
drwxr-xr-x jao      jao              4096 /tmp/d/hi
-rw-r--r-- jao      jao                 0 /tmp/d/hi/a.txt
-rw-r--r-- jao      jao                 0 /tmp/d/hi/b.txt
dr-------- root     root             4096 /tmp/d/nope
{c550:Error(Cannot explore /tmp/d/nope: permission denied)}
drwxr-xr-x jao      jao              4096 /tmp/d/welcome
-rw-r--r-- jao      jao                 0 /tmp/d/welcome/c.txt
-rw-r--r-- jao      jao                 0 /tmp/d/welcome/d.txt

Notice that the {r:nope} directory is listed as before, but we get an
error on the attempt to go inside of it. The position of
the {r:Error} in the output indicates when the
attempt was made -- between listing the {r:hi} and {r:welcome} directories.

For Linux executables, each line of {n:stderr} is turned into an {n:Error}
and written to the same stream receiving {n:stdout}.
'''
