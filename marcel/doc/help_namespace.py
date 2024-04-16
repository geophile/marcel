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
Python code always runs in the context of a namespace. The {i:marcel namespace}
is the namespace used by marcel to execute user-supplied code. During startup, 
the configuration script, usually {n:~/.config/marcel/startup.py}, is executed. At this point, the 
marcel namespace contains a few variables (such as {n:USER}, {n:HOME},
and {n:PROMPT}), and functions for configuring access to various
resources (e.g. {n:define_remote}).

The configuration script is ordinary Python code, so you can use
{n:import} statements to add symbols from modules, and define your own
variables, functions and classes for use in marcel commands. Examples follow.

{b:Imports:}

You can use marcel as a calculator, by using the {n:map} command,
specifying a function with no arguments.

{p,wrap=F,indent=4}
    {c500b:M} {c021b:jao@cheese}:{c033b:~$} map (5 + 7)
    12

To compute the golden ratio:
{p,wrap=F,indent=4}
    {c500b:M} {c021b:jao@cheese}:{c033b:~$} map ((1 + sqrt(5)) / 2)
    {c550:Error(map((1 + sqrt(5)) / 2) failed on : name 'sqrt' is not defined}

This fails because {r:sqrt} is not a builtin function in Python. It comes from
the {n:math} module. If this line is added to {n:startup.py}:
{p,wrap=F,indent=4}
    from math import sqrt

then {r:sqrt} can be used:
{p,wrap=F,indent=4}
    {c500b:M} {c021b:jao@cheese}:{c033b:~$} map ((1 + sqrt(5)) / 2)
    1.618033988749895

You should probably include {n:import marcel.builtin} in your configuration
file. This includes a collection of functions useful for shell operations.
Run {n:help builtin} for more information.

{b:Definitions:}

You can also define symbols in the usual way, assigning variables,
defining functions and classes. Any symbols you define will be available
in your marcel commands.

For example, if you put this code in your configuration script:
{p,wrap=F,indent=4}
    import time
    def current_time():
        return time.asctime(time.gmtime())

Then you can use the {r:current_time} function in your commands, e.g.
{p,wrap=F,indent=4}
    {c500b:M} {c021b:jao@cheese}:{c033b:~$} timer 1 | map (t: (current_time(), t))
    ('Sat Apr 25 17:58:31 2020', 1587837511.0)
    ('Sat Apr 25 17:58:32 2020', 1587837512.0)
    ('Sat Apr 25 17:58:33 2020', 1587837513.0)
    ...
'''
