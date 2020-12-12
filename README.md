What's New
----------

Sometimes it's convenient to have something like line numbers, because
you want to treat inputs differently, based on their position in the 
input stream. For example, if you have CSV input, you might want
to ignore the first line, containing headers. You can do this as follows:

```shell
read --csv foo.csv | head -1
```

This reads `foo.csv`, and keeps all lines except for the first.

But this isn't very general. E.g., you might want to keep every other 
input, starting with the first. This is now possible through the addition
of the `pos()` builtin function. Each operator has its own position counter,
which can be accessed using `pos()`. So to keep evey other line of a file
`foo.txt`, starting with the first line:

```shell
read foo.txt | select (line: pos() % 2 == 0)
```

`read` has its own counter, but it is inaccessible, as the `read` operator
does not allow for a function argument which could reference `pos()`. However,
the next operator, `select`, also has a counter, also accessible through
`pos()`, and that is the counter that is tested.

To see this fact more clearly, that each operator has its own `pos()`, 
look at this command:

```shell
gen 5 1000 \
| map (x: (x, pos())) \
| select (x, y: x % 2 == 0) \
| map (x, y: (x, y, pos()))
```

- `gen 5 1000`: Generates the stream 1000, 1001, 1002, 1003, 1004.
- `map(x: (x, pos()))`: This appends a position to each input item, yielding
  (1000, 0), (1001, 1), (1002, 2), (1003, 3), (1004, 4).
  
- `select(x, y: x % 2 == 0)`: For each input row, keep those for which x is 
  even, so: (1000, 0), (1002, 2), (1004, 4).
  
- `map(x, y: (x, y, pos()))`: This attaches a new `pos()` value for each input.
- The command's output is: (1000, 0, 0), (1002, 2, 1), (1004, 4, 2).

Marcel
======

[Marcel is a shell](https://www.youtube.com/watch?v=VF9-sEbqDvU). 
The main idea is to rely on piping as the primary
means of composition, as with any Unix or Linux
shell. However, instead of passing strings from one command to the
next, marcel passes Python values: builtin types such as lists,
tuples, strings, and numbers; but also objects representing files and
processes.

Linux has extremely powerful commands such as `awk` and `find`.  Most
people know how to do a few simple operations using these commands.
But it is not easy to exploit the full power of these commands
due to their reliance on extensive "sublanguages" which do:

* __Filtering__: What data is of interest?
* __Processing__: What should be done with the data?
* __Formatting__: How should results be presented?

By contrast, marcel has no sublanguages.  You use marcel operators
combined with Python code to filter data, process it, and control
command output.

The commands and syntax supported by a shell constitute a language
which can be used to create scripts. Of course, in creating a script,
you rely on language features that you typically do not use
interactively: control structures, data types, and abstraction
mechanisms (e.g. functions), for example. 
Viewed as a programming language, shell scripting languages 
are notoriously bad. I didn't think it was wise to bring another one
into the world. So marcel takes a different
approach, using Python as a scripting language, (see below for more 
on scripting).

Pipelines
---------

Marcel provides commands, called _operators_, which do the basic work of a shell. 
An operator takes a _stream_ of data as input, and generates another stream as output.
Operators can be combined by pipes, causing one operator's output to be the next operator's input.
For example, this command uses the `ls` and `map` operators to list the
names and sizes of files in the `/home/jao` directory:

```shell script
ls /home/jao | map (f: (f, f.size))
``` 

* The `ls` operator produces a stream of `File` objects, representing the contents
of the `/home/jao` directory.
* `|` is the symbol denoting a pipe, as in any Linux shell.
* The pipe connects the output stream from `ls` to the input stream of the next
operator, `map`.
* The `map` operator applies a given function to each element of the input stream,
and writes the output from the function to the output stream. The function is enclosed
in parentheses. It is an ordinary Python function, except that the keyword `lambda` is optional.
In this case, an incoming `File` is mapped to a tuple containing the file and the file's size.

A `pipeline` is a sequence of operators connected by pipes. They can be used directly
on the command line, as above. They also have various other uses in marcel. For example,
a pipeline can be assigned to a variable, essentially defining a new operator.
For example, here is a pipeline, assigned to the variable `recent`, which selects
`File`s modified within the past day:

```shell script
recent = [select (file: now() - file.mtime < hours(24))] 
``` 

* The pipeline being defined is bracketed by `[...]`. (Without the brackets, marcel would
attempt to evaluate the pipeline immediately, and then complain because the parameter
`file` is not bound.)
* The pipeline contains a single operator, `select`, which uses a function to define
the items of interest. In this case, `select` operates on a `File`, bound to the 
parameter `file`. 
* `now()` is a function defined by marcel which gives the current time in seconds since
the epoch, (i.e., it is just `time.time()`).
* `File` objects have an `mtime` property, providing the time since the last content modification.
* `hours()` is another function defined by marcel, which simply maps hours to seconds, i.e.,
it multiplies by 3600.

This pipeline can be used in conjunction with any pipeline yielding files. E.g., to locate
the recently changed files in `~/git/myproject`:

```shell script
ls ~/git/myproject | recent
```

Functions
---------

As shown above, a number of operators, like `map` and `select`, take Python functions as 
command-line arguments. Functions can also be invoked to provide function arguments.
For example, to list the contents of your home directory, you could write:

```shell script
ls /home/(USER)
```

This concatenates the string `/home/` with the string resulting from the evaluation of
the expression `lambda: USER`. `USER` is a marcel environment variable identifying the
current user, so this command is equivalent to `ls ~`.

If you simply want to evaluate a Python expression, you could use the `map` operator, e.g.

```shell script
map (5 + 6)
```  

which prints `11`. In a situation like this, marcel also permits you to omit `map`; it is
implied, so this also works:

```shell script
(5 + 6)
```

Executables
-----------

In addition to using built-in operators, you can, of course, call any executable.
Pipelines may contain a mixture of marcel operators and host executables. Piping between
operators and executables is done via streams of strings.

For example, this command combines operators and executables. 
It scans `/etc/passwd` and lists the usernames of 
users whose shell is `/bin/bash`. 
`cat`, `xargs`, and `echo` are Linux executables. `map` and `select` are marcel operators.
The output is condensed into one line through
the use of `xargs` and `echo`. 

```shell script
cat /etc/passwd \
| map (line: line.split(':')) \
| select (*line: line[-1] == '/bin/bash') \
| map (*line: line[0]) \
| xargs echo
```

* `cat /etc/passwd`: Obtain the contents of the file. Lines are piped to subsequent commands.
* `map (line: line.split(':'))`: Split the lines at the `:` separators, yielding 7-tuples.
* `select (*line: line[-1] == '/bin/bash')`: select those lines in which the last field is `/bin/bash`.
* `map (*line: line[0]) |`: Keep the username field of each input tuple.
* `xargs echo`: Combine the incoming usernames into a single line, which is printed to `stdout`.

Shell Features
--------------

Marcel provides:

* __Command history:__ A `history` operator, rerunning and editing of previous commands,
reverse search, etc.
* __Customizable prompts:__ Configured in Python, of course.
* __Tab completion:__ For operators, flags, and filename arguments.
* __Help:__ Extensive help facility, providing information on concepts, objects,
and operators.
* __Customizable color highlighting:__ The colors used to render output for builtin types such 
as `File` and `Process`, and `help` output can be customized too.
* __Dynamic reconfiguration:__ Changes to configuration and startup scripts are picked up without restarting.

Scripting
---------

Marcel's syntax for constructing and running pipelines, and defining and using
variables and functions, was designed for interactive usage. Instead of extending
this syntax to a full-fledged scripting language, marcel provides a Python API,
allowing Python to be used as the scripting language.
While Python is
sometimes considered to _already be_ a scripting language, it isn't really. 
Executing shell commands from Python code is cumbersome. You've got to use
`os.system`, or `subprocess.Popen`, and write some additional code to
do the integration.

Marcel provides a Python module, `marcel.api`,
which brings shell commands into Python in a much cleaner way. For
example, to list file names and sizes in `/home/jao`:

```python
from marcel.api import *

for file, size in ls('/home/jao') | map(lambda f: (f, f.size)):
    print(f'{file.name}: {size}')
```
This code uses the `ls` and `map` functions, provided by `marcel.api`. These correspond to
marcel operators that you can use on the command line. Output from the `ls` is a stream
of `File`s, which are piped to `map`, which maps files to (file, file size) tuples. 
`ls ... | map ...` defines a pipeline (just as on the command line). The Python
class representing pipelines defines `__iter__`, so that the pipeline's output can be
iterated over using the standard Python `for` loop.


Installation
------------

To install marcel:
```shell script
python3 -m pip install marcel
```

This command installs marcel for the current user. To install for the entire system,
use `sudo python3 -m pip install --prefix ...` instead. (The value of the `--prefix` flag should
be something like `/usr/local`.)

Marcel depends on [dill](https://pypi.org/project/dill/). This package
will be installed automatically if needed, when marcel is installed
via pip.
