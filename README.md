Marcel
======

[Marcel is a shell](https://www.youtube.com/watch?v=VF9-sEbqDvU). 
The main idea is to rely on piping as the primary
means of building up functionality, as with any Unix or Linux
shell. However, instead of passing strings from one command to the
next, marcel passes Python values: builtin types such as lists,
tuples, strings, and numbers; but also objects representing files and
processes.

Linux has extremely powerful commands such as `awk` and `find`.  Most
people know how to do a few simple operations using these commands,
but cannot easily exploit the full power of these command due to their
reliance on extensive "sublanguages" which do:

* __Filtering__: What data is of interest?
* __Processing__: What should be done with the data?
* __Formatting__: How should results be presented?

By contrast, if you know Python, then you already know the language
used by marcel.  You use Python to filter data,
process it, and control command output.

The commands and syntax supported by a shell constitute a language
which can be used to create scripts. Of course, in creating a script,
you rely on language features that you typically do not use
interactively: control structures, data types, and abstraction
mechanisms (e.g. functions), for example. And 
from a lanugage point of view,
shell scripting is notoriously bad. Marcel takes a different
approach, using Python as a scripting language. While Python is
sometimes considered to already be a scripting language, it isn't really. 
Executing shell commands from Python code is cumbersome. You've got to use
`os.system`, or `subprocess.Popen`, and write some additional code to
do the integration. Marcel provides a Python module, `marcel.api`,
which brings shell commands into Python in a much cleaner way. For
example, to list file names and sizes in `/home/jao`:

```python
from marcel.api import *

for file, size in ls('/home/jao') | map(lambda f: (f, f.size)):
    print(f'{file.name}: {size}')
```

This is a standard Python for loop, iterating over the results of the `ls` command,
piped to a function which maps files to (file, file size) tuples, which are then printed.

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
a pipeline can be assigned to a variable, essentially defining a function.
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
implied. So writing `(5 + 6)` as the entire command is also supported.

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
* __Customizable color highlighting:__ The colors used to render output for builtin types such 
as `File` and `Process`, and `help` output can be customized too.
* __Tab completion:__ For operators, flags, and filename arguments.
* __help:__ Extensive help facility, providing information on concepts, objects,
and operators.

Scripting
---------

Marcel's syntax for constructing and running pipelines, and defining and using
variables and functions, was designed for interactive usage. Extending this syntax
to a full scripting language is pointless, as it would be unlikely to yield a first-rate
implementation of a first-rate language. Instead, my approach is to make it possible
to use Python as a scripting language by adding a marcel API. Recall this example:

```
recent = [select (file: now() - file.mtime < hours(24))] 
ls ~/git/myproject | recent
```

The same thing could be done from Python after importing the marcel API:

```python
from marcel.api import *

recent = select(lambda file: now() - file.mtime < hours(24))
for file in ls('~/git/myproject') | recent:
    print(f'{file}')
```

* Each marcel operator is represented by a function imported by `marcel.api`.
* Command-line arguments turn into function arguments. For `select`, note that
its function argument is the same as in the shell version, except that the `lambda`
keyword is now required, because we are now bound by Python syntax rules.
* `ls(...) | recent` defines a marcel pipeline. The Python class representing pipelines
defines `__iter__` so that the pipeline can be used directly in a Python `for` loop.


Installation
------------

To install marcel:
```shell script
python3 -m pip install marcel
```

This command installs marcel for the current user. To install for the entire system,
use `sudo python3 -m pip install --prefix ...` instead. (The value of the `prefix` flag should
be something like `/usr/local`.)

Marcel depends on [dill](https://pypi.org/project/dill/). This package
will be installed automatically if needed, when marcel is installed
via pip.
