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
The {n:history} operator prints previously run commands, e.g.

{p,wrap=F,indent=4}
M jao@cheese:~$ history
...
  418:  cd ../..
  419:  git status
  420:  git diff > /tmp/marcel.diff
  421:  git commit -a

This is done by generating a stream of {n:HistoryRecord} objects,
which are then printed by an implicit {n:out} operator.
The purpose of providing {n:HistoryRecord}s (instead of tuples) is to
benefit from marcel's rendering capabilities. {n:HistoryRecord}'s rendering
methods format and colorize the objects, allowing for more readable output
from the {n:history} operator.

As usual, you can process the objects in this stream with other operators.
A {n:HistoryRecord} object has two properties:

{L,indent=4:6}- {r:id}: The identifier of the command within the history.
{L,indent=4:6}- {r:command}: The command itself.

E.g., to select git commands from the command history:

{p,wrap=F,indent=4}
history | select (h: 'git' in h.command)
'''
