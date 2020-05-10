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
The default marcel prompt is {n:$}. 
You can customize the prompt by assigning to the {r:PROMPT}
environment variable, 
in your configuration script, (run
{n:help configuration} for more information on configuration). For example:
{p,wrap=F,indent=4}
PROMPT = [
    COLOR_RED_BOLD,
    'M ',
    Color(1, 2, 4, BOLD),
    USER,
    '@',
    HOST,
    COLOR_WHITE,
    ':',
    Color(0, 3, 3, BOLD),
    lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD,
    '$ '
]

This produces the following prompt (for me):

{p,indent=4}{c500b:M} {c124b:jao@cheese}:{c033b:~$}

(The {c500b:M} is there to remind me, while developing marcel, that I am
running marcel, not bash.)

Notes:
{L}- The value assigned to {r:PROMPT} is a list containing colors, strings, and functions
   evaluating to colors or strings. A color is in effect for all following strings, until
   a different color is specified. (Run {n:help color} for more information on colors.)
{L}- {r:COLOR_RED_BOLD} has been defined previously, and is used to establish a color.
{L}- {r:'M '}: This string is displayed using the current color, {r:COLOR_RED_BOLD}.
{L}- {r:Color(0, 2, 1, BOLD)}: Establishes a new color.
{L}- {r:USER}, {r:HOST}, {r:HOME}, {r:PWD} are variables initialized by marcel representing,
   respectively, the current username, the current hostname, the user's home directory,
   and the current directory.
{L}- {r:lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD}: 
This is a function computing the rendering of the current directory. If the
current directory, (stored in {r:PWD}), is under
the {r:HOME} directory, then display a path starting with {r:~}. Otherwise
print {r:PWD} as is. This expression is not evaluated immediately, (at startup),
but is instead turned into a function, through the use of {r:lambda}.
Because {r:PWD} likely changes over time, (as the user executes
{n:cd}, {n:pushd}, and {n:popd} operations), the expression needs to
be evaluated each time the prompt is displayed.

For multi-line commands, a second prompt, specified in the variable {r:PROMPT_CONTINUATION}
is used, e.g.

{p,wrap=F,indent=4}
PROMPT_CONTINUATION = [
    COLOR_RED_BOLD,
    'M ',
    Color(3, 4, 0, BOLD),
    '+$    '
]
'''
