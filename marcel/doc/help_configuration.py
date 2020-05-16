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
Several marcel operators take function arguments. These functions 
run in a namespace maintained by marcel. This namespace contains
the equivalent of environment variables from other shells. For example,
there are {n:USER} and {n:PWD} variables, which contain the values of
the user and the current directory.

Marcel is configured by running the configuration file
{n:~/.marcel.py} on startup. This script operates on the marcel
namespace, allowing you to customize the prompt, the color scheme used
for output, database and remote host login configuration, as well as
defining any other symbols you would like to have available. As usual,
these symbols can be defined by imports, by assigning variables, and
by defining functions and classes.

For more detail on configuration run {n:help} on the following topics:

{L}- {n:color}: Customizing the color scheme.
{L}- {n:prompt}: Customizing the prompt.
{L}- {n:namespace}: Adding symbols to the marcel namespace.
{L}- {n:remote}: Configuring remote access.
'''
