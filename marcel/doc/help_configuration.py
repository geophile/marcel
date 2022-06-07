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
Marcel is configured and customized by running the startup script {n:startup.py}.
This script is typically located in the directory {n:~/.config/marcel},
but may be in a different location, specified by the environment
variable {n:XDG_CONFIG_HOME}.

In this script, you can 
customize the prompt, output colorization, remote host configuration,
as well as defining any other symbols you would like to have
available. As usual, these symbols can be defined by imports, by
assigning variables, and by defining functions and classes.

These symbols exist in an ordinary Python namespace, the {i:marcel
namespace}. This namespace is used when evaluating functions, (such as
are used in conjunction with the {n:map} and {n:select} operators).
Variables in the marcel namespace are equivalent to environment
variables in other shells. So, for example, the {n:USER} and {n:PWD}
variables are present in the marcel namespace, and identify the
current user and current directory, respectively.

Further information can be obtained by running {n:help} on the
following topics:

{L}- {n:color}: Customizing the color scheme.
{L}- {n:prompt}: Customizing the prompt.
{L}- {n:namespace}: Adding symbols to the marcel namespace.
{L}- {n:remote}: Configuring remote access.
{L}- {n:startup}: Running scripts on startup.
'''
