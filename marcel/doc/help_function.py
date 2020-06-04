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
Several marcel operators rely on {i:functions}. For example, you can
list {n:.mp3} files anywhere inside your home directory as follows:

{L,wrap=F}ls -fr ~ | select (lambda f: f.suffix.lower() == '.mp3')

{r:ls -fr ~} lists files only ({r:-f}), recursively ({r:-r}), starting with
the home directory ({r:~}). The {r:ls} operator yields {n:File} objects
which are then piped to the {r:select} operator.

{r:select} has a function, delimited by parentheses. This function binds
each {n:File} arriving on the input stream, to the parameter {r:f}. The
function returns True if the {n:File}'s suffix is {n:.mp3}, False
otherwise. {n:File} objects support the {n:pathlib.Path} interface, so
{r:f.suffix} returns the extension of {n:File} {r:f}, (including the
dot). Then, {r:.lower()} converts the extension to lower case, and the
resulting string is compared to {r:.mp3}.

All marcel operators that rely on functions use the same syntax demonstrated 
here: The function is enclosed in parentheses; the parameters are bound
to components of incoming tuples. And in all cases, the {n:lambda} keyword
can be omitted. So the preceding example could be rewritten as:

{L,wrap=F}ls -fr ~ | select (f: f.suffix.lower() == '.mp3')

Marcel functions run in a namespace maintained by marcel. Run
{n:help namespace} for more information on this topic.

{b:Evaluating functions to compute command arguments}

Functions can also be used to compute the value of command arguments. For example,
to condense an input stream into groups of size 10, you can use the {n:window}
operator:

{L,wrap=F}... | window --disjoint 10 | ...

If your group size is stored in the {r:GROUP_SIZE} variable, you could obtain
the value of the variable by using a function:

{L,wrap=F}... | window --disjoint (GROUP_SIZE) | ...

Recall that marcel allows omission of the {n:lambda} keyword, so {r:(GROUP_SIZE)}
is equivalent to {r:(lambda: GROUP_SIZE)}, i.e., a function of zero arguments
that returns the value of the {r:GROUP_SIZE} variable. That variable
is present in the marcel namespace, and so is available to the function
being executed.

{b:Marcel as a calculator}

You can also evaluate a function as the first command in a pipeline. This
allows you to use marcel as a calculator, e.g. 

{L}(hex(123))

This is shorthand for:

{L}map (lambda: hex(123))

which runs the builtin Python function {r:hex} with the input {r:123}, and prints
the result, {r:0x7b}.

Values obtained in this way can, of course, be piped. For example, here is 
a marcel implementation of FizzBuzz:

{L,indent=4,wrap=F}
(range(1, 101)) \\\\
| expand \\\\
| map (x: 'FizzBuzz' if x % 15 == 0 else \\\\
          'Fizz' if x % 3 == 0 else \\\\
          'Buzz' if x % 5 == 0 else \\\\
          x)

Explanation:

{L,wrap=F}- {r:(range(1, 101))} creates a range of integers, from 1 to 100 inclusive.
{L,wrap=F}- {r:expand} yields a stream containing each of those integers.
{L,wrap=F}- {r:map (...)} applies the FizzBuzz rules to each integer.
'''
