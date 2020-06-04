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
Marcel is a shell. As in any Linux shell, there are commands which
can be executed, and the output from one command
can be piped to another.  The conventional piping syntax is used: {n:|}. Linux
pipes stream unstructured text between commands. In marcel, streams
carry arbitrary Python values.

Marcel is implemented in, and based on the Python language. Whereas
other shells invent new languages for control constructs, expressions,
and so on, marcel simply relies on Python. So the {n:map} operator takes
a stream of Python objects as input, and generates a stream of Python
objects as output. Each output object is computed by applying a Python
function to an input object. For example, this marcel code generates
a sequence of 100 integers, 0 through 99, and, outputs the each number
along with its square root:

{p,wrap=F}
    gen 100 | map (lambda x: (x, x**0.5))

Note that the Python function, mapping {r:x} to the tuple {r:(x, x**0.5)}
is enclosed in parentheses, as is the case whenever a function is
required. Marcel permits the {n:lambda} keyword to be omitted.

The following topics will explain these concepts in more detail:

{p,wrap=F}
    - {n:command}
    - {n:function}
    - {n:pipeline}
'''
