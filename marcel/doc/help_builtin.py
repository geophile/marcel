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
Your configuration script, {n:.marcel.py} should do the following to
make a few useful functions available to your commands:

{L}from marcel.builtin import *

While the {n:from ... import *} idiom is discouraged, it seems like the
right tool to use here. Otherwise, you need to use qualified function names,
e.g. {n:marcel.builtin.now()}; or explicitly create a new variable in the namespace
(e.g. {n:now = marcel.builtin.now}). 

The functions in {n:marcel.builtin} are:

{L,indent=4:6}- {n:processes}: A list containing a {n:Process} object for each
current process.

{L,indent=4:6}- {n:now}: The current time as a float, as seconds since the epoch.

{L,indent=4:6}- {n:minutes}: Converts minutes to seconds, for comparison with epoch
time calculations. E.g. minutes(1) returns 60.

{L,indent=4:6}- {n:hours}: Converts hours to seconds.

{L,indent=4:6}- {n:days}: Converts days to seconds.
'''
