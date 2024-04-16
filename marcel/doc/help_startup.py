# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
If the marcel startup script, typically {n:~/.config/marcel/startup.py}, defines the variable 
{r:RUN_ON_STARTUP}, then the commands listed will be run
when marcel starts. The value of this variable should be a string,
with one command per line, (so probably a triple-quoted string).

{b:Example}

Suppose {n:startup.py} defines {r:RUN_ON_STARTUP} as follows:

{p,indent=4,wrap=F}RUN_ON_STARTUP = """
ext = (| e: select (f: f.suffix == '.' + e) |)
recent = (| d: ls -fr | select (f: now() - f.mtime < days(float(d))) |)
"""

In your marcel session, you can now use the variables {r:ext} and {r:recent}.

{L}- {r:ext} receives a stream of {n:File} objects, and outputs those whose extension matches
the given extension, {r:e}. E.g. {n:ls -fr | ext py} explores the current directory
recursively, and lists files with a {n:.py} extension.

{L}- {r:recent} receives a stream of {n:File} objects, and outputs those that have been modified
in the previous {r:d} days.
'''
