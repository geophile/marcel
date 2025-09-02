What's New
----------

This release contains a major overhaul of marcel internals, intended to anticipate
Python changes, and to enable porting.

Most marcel commands execute as jobs, which can be suspended, run in the background, 
and brought to the foreground, as in other shells. The `multiprocessing` module is used
to run a job in a process. This module can start processes in one of three ways:

- **fork**: The child process inherits the parent's resources, including memory. (The memory is not shared,
as in threading. Changes made by the child are not visible by the parent.)
- **spawn**: The child process is a new Python interpreter, and resources, including memory, are not shared.
- **forkserver**: Like fork, but the forking is done by a server process created for the purpose of
forking processes.

Fork is the default on Linux. Spawn is the default on MacOS, and will become the default on 
Python. Prior to this release, marcel relied on fork. But it looks like spawn really needs to be
supported, especially to support MacOS. Fork on MacOS is known to possibly cause crashes. 

Marcel environment variables are kept in a *namespace*, which serves as a Python namespace for
the execution of Python functions that appear in marcel commands. The problem was that the marcel
namespace worked well with the fork model of multiprocessing, but not spawn. With fork, the namespace
exists in memory shared with the child process. But when a process is spawned, the namespace isn't 
shared, it has to be pickled and transmitted, and the namespace contains values that could
not be pickled: e.g. Python functions and modules.  

So in order to support the spawn model of multiprocessing, the namespace implementation had to be
overhauled. Values that can be pickled are pickled. Others values require special handling.
For example, suppose a user has run the command `import math`. The math module cannot be pickled.
But by noting the import, and replaying it in the child process, we can avoid pickling the math
module, but still transmit it to the child process.

For now, marcel uses the spawn model of multiprocessing by default. This results in noticeably slower
operation, imposing
a fraction of a second delay to command execution. (It might be worth investigating forkserver
to fix this problem.) If this delay is intolerable, or you have found a bug and it seems 
like spawning is implicated, then to use fork instead, set the environment variable 
`MARCEL_MULTIPROCESSING_START_METHOD`. Valid values are `fork` and `spawn`. 

With spawn multiprocessing supported, MacOS support should now be possible. Watch this space for
information on MacOS support.

*Late update: Marcel is now working on MacOS!* 

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
ls /home/jao | map (lambda f: (f, f.size))
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
recent = (| select (file: now() - file.mtime < days(1)) |) 
``` 

* The pipeline being defined is bracketed by `(|...|)`. (Without the brackets, marcel would
attempt to evaluate the pipeline immediately, and then complain because the parameter
`file` is not bound.)
* The pipeline contains a single operator, `select`, which uses a function to define
the items of interest. In this case, `select` operates on a `File`, bound to the 
parameter `file`. 
* `now()` is a function defined by marcel which gives the current time in seconds since
the epoch, (i.e., it is just `time.time()`).
* `File` objects have an `mtime` property, providing the time since the last content modification.
* `days()` is another function defined by marcel, which simply maps days to seconds, i.e.,
it multiplies by 24 * 60 * 60.

This pipeline can be used in conjunction with any pipeline yielding files. E.g., to locate
the recently changed files in `~/git/myproject`:

```shell script
ls ~/git/myproject | recent
```

Functions
---------

As shown above, a number of operators, like `map` and `select`, take Python functions as 
command-line arguments. Functions can also be invoked to obtain the value of an
environment variable.
For example, to list the contents of your home directory, you could write:

```shell script
ls /home/(USER)
```

This concatenates the string `/home/` with the string resulting from the evaluation of
the expression `lambda: USER`. `USER` is a marcel environment variable identifying the
current user, (so this command is equivalent to `ls ~`).

If you simply want to evaluate a Python expression, you could use the `map` operator, e.g.

```shell script
map (5 + 6)
```  

which prints `11`. Marcel permits the `map` operator to be inferred, 
so this also works:

```shell script
(5 + 6)
```

In general, you can elide `map` from any pipeline.

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
| map (user, *_: user) \
| xargs echo
```

* `cat /etc/passwd`: Obtain the contents of the file. Lines are piped to subsequent commands.
* `map (line: line.split(':'))`: Split the lines at the `:` separators, yielding 7-tuples.
* `select (*line: line[-1] == '/bin/bash')`: select those lines in which the last field is `/bin/bash`.
* `map (user, *_: user) |`: Keep the username field of each input tuple.
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

This code uses the `ls` and
`map` functions, provided by `marcel.api`. These correspond to the
marcel operators `ls` and `map` that you can use on the command
line. Output from the `ls` is a stream of `File`s, which are piped
to `map`, which maps files to (file, file size) tuples.  `ls ... |
map ...` defines a pipeline (just as on the command line). The
Python class representing pipelines defines ``iter``, so that
the pipeline's output can be iterated over using the standard
Python `for` loop.


Installation
------------

To install marcel locally (i.e., available only to your username):

```shell script
python3 -m pip install marcel
```

This command installs marcel for the current user. To install for the entire system,
use `sudo python3 -m pip install --prefix ...` instead. (The value of the `--prefix` flag should
be something like `/usr/local`.)

Marcel depends on [dill](https://pypi.org/project/dill/), [psutil](https://pypi.org/project/psutil/),
and [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io). These packages
will be installed automatically if needed, when marcel is installed
via pip.
