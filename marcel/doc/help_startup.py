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
If the marcel configuration file, {n:~/.marcel.py}, defines the variable 
{r:LOAD_ON_STARTUP}, then the scripts specified by this variable will be run
when marcel starts. The value of this variable can be a string identifying
a script, or a list or tuple whose elements are such strings.

The startup scripts can contain any marcel commands. Typically, then will 
define variables that you would like to have available when using marcel.

{b:Example}

Suppose {n:~/.marcel.py} defines {r:LOAD_ON_STARTUP} as follows:

{L,wrap=F}LOAD_ON_STARTUP = '~/.init.marcel'

And {r:~/.init.marcel} contains these commands:

{p,wrap=F,indent=4}
recent = [select (f: now() - f.mtime < days(1))]
cat = [map (f: (f, f.readlines()) | expand 1]

In your marcel session, you can now use the variables {r:recent} and {r:cat}.

{L}- {r:recent} receives a stream of {n:File} objects, and outputs those that have been modified
in the past day.
{L}- {r:cat} receives a stream of {n:File} objects, and outputs (file name, line of file) tuples
for each line in each {n:File}. (So it is similar to the Linux command by the same name.)
'''
