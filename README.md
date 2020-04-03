Marcel
======

[Marcel is a shell](https://www.youtube.com/watch?v=VF9-sEbqDvU). 
The main idea is to rely on piping as the primary
means of building up functionality, as with any Unix or Linux
shell. However, instead of passing strings from one command to the
next, marcel passes Python objects: builtin types such as lists,
tuples, strings, and numbers; but also objects representing files and
processes.

Marcel is the successor to [osh](http://github.com/geophile/osh) 
(Object SHell). Osh
is based on the same ideas, but it is not a full-fledged shell;
it is an executable
that takes shell-like commands as input, composes them using pipes, 
and passes Python objects,
as Marcel does. Marcel improves on osh in a number of ways:

* Marcel is a full-fledged shell.

* A planned abstraction mechanism is to offer pipelines as first-class constructs. 
This will allow for more complex commands (which combine multiple pipelines), and the composition of pipelines.

* Marcel started with the osh code base (for commands and pipelines), but cleaned up a number of ugly hacks and 
non-pythonic constructs.

* Osh requires Python 2.x. Marcel requires Python 3.x. (Whether you regard that as an improvement is 
obviously subjective.)

Shell Features
--------------

Marcel provides:

* Command history and recall, including correct handling of multi-line commands. (Muti-line support
is implemented using [multilinereader](https://github.com/geophile/multilinereader).)

* Searching of command history (e.g. ctrl-R).

* Editing of last command in the editor of your choice.

* Context-sensitive tab completion.

* Prompt customization.

* Customizable highlighted output of file and process listings.

Example
-------
Print all processes running Python:

    M jao@cheese:~$ ps | select (p: p.commandline.startswith('/usr/bin/python')) 

* `ps`: Generates a stream of `Process` objects.

* `|`: Pipes the processes to the next command. (Note that `|` is not
a Unix pipe. The entire command runs in a single Python process.)

* `select (p: ...)`: Selects processes, `p`, for which the
condition is true: The commandline of `p` starts with
`'/usr/bin/python'`. The code inside the parens is a Python function, (marcel permits
the `lambda` keyword to be omitted).

* The output renders each qualifying `Process` using formatting
specified as part of the implementation of
the `Process` object. 

```
      921 /usr/bin/python3 /usr/lib/system76-driver/system76-daemon
      933 /usr/bin/python3 /usr/bin/networkd-dispatcher --run-startup-triggers
     2228 /usr/bin/python3 /usr/lib/hidpi-daemon/hidpi-daemon
     2295 /usr/bin/python3 /usr/lib/hidpi-daemon/hidpi-notification
```


Another Example
---------------
Find all files recursively, and then find the sum of file sizes,
grouped by extension:

```
    M jao@cheese:~/git/marcel$ ls -fr | map (f: (f.path.suffix, 1, f.size)) | red . + +
    ('.xml', 5, 28176)
    ('.iml', 1, 819)
    ('.py', 59, 146934)
    ('.txt', 12, 20814)
    ('', 646, 596689)
    ('.sample', 11, 18844)
    ('.pyc', 43, 129403)
    ('.md', 1, 1378)
```

* `ls -fr`: List just files (`-f`) recursively (`-r`).

* `map(f: (f.path.suffix, 1, f.size))`: Map each file, `f`, to a tuple containing the file's 
extension, the integer 1, and the file size.

* `red . + +`: Reduce the incoming stream, grouping by the file extensions (in the tuple position 
identified by
the `.`), and summing up the `1`s (to obtain the count for that extension), 
and the sizes.

Executables
-----------

In addition to using built-in operators, you can, of course, call any executable provided by
the operating system. Pipelines may contain a mixture of operators and executables. The stdout of
an executable pipes into an operator as a string. Output from an operator is turned into a string
when it is piped into an executable.

For example, this command scans `/etc/passwd` and lists the usernames of 
users whose shell is `/bin/bash`. 
`cat`, `xargs`, and `echo` are Linux commands. `map` and `select` are marcel operators.
The output is condensed into one line through
the use of `xargs` and `echo`. 

    cat /etc/passwd | \
    map (line: line.split(':')) | \
    select (*line: line[-1] == '/bin/bash') | \
    map (*line: line[0]) | \
    xargs echo

* The command is broken up across a few lines using a \ at the end of each non-terminal line.

* `cat /etc/passwd`: Obtain the contents of the file. Lines are piped to subsequent commands.

* `map (line: line.split(':'))`: Split the lines at the `:` separators, yielding 7-tuples.

* `select (*line: line[-1] == '/bin/bash')`: select those lines in which the last field is `/bin/bash`.

* `map (*line: line[0]) |`: Keep the username field of each input tuple.

* `xargs echo`: Combine the incoming usernames into a single line, which is printed to `stdout`.



Remote access
-------------

Marcel can submit commands to all of the nodes in a cluster, and then combine the results.
For example, a cluster named `qa` can be configured in `~/.marcel.py`:

```
    qa = Cluster('qa')
    qa.hosts = ['192.168.10.100', '192.168.10.101']
    qa.user = 'qa_joe'
    qa.identity = '~qa_joe/home/.ssh/id_rsa'
```

Then, to get a list of files in `/usr/local/bin` in each node of the cluster:

    M jao@cheese:~$ @qa [ ls /usr/local/bin ]

- `@qa [ ... ]` executes the bracketed commands on each node of the `qa` cluster.

- The output includes an identification of the node that produced the output, e.g.

```
    ('192.168.100.0', .)
    ('192.168.100.0', decompile)
    ('192.168.100.0', nosetests)
    ('192.168.100.0', nosetests-2.7)
    ('192.168.100.0', nosetests-3.4)
    ('192.168.100.0', piximporter)
    ('192.168.100.1', .)
    ('192.168.100.1', decompile)
    ('192.168.100.1', erdo)
    ('192.168.100.1', movements)
```


Errors
------

The POSIX model of `stdout` and `stderr` streams distinguishes normal output from errors.
An unfortunate aspect of this approach is that the interleaving of normal output and errors is lost.
A marcel pipeline generates a stream of values, and each value has a type. This allows for normal
and error output to be combined in one stream, since error values can be identified by type.

For example, directory `/tmp/d` has three directories:
 
 ```
    M jao@cheese:/tmp/d$ ls
    drwxr-xr-x jao      jao              4096 /tmp/d/hi
    dr-------- z        z                4096 /tmp/d/nope
    drwxr-xr-x jao      jao              4096 /tmp/d/welcome
```

The `nope` directory cannot be visited, due to permissions. If we try to list all files
and directories recursively:  

```
    M jao@cheese:/tmp/d$ ls -r
    drwxr-xr-x jao      jao              4096 /tmp/d/hi
    -rw-r--r-- jao      jao                 0 /tmp/d/hi/a.txt
    -rw-r--r-- jao      jao                 0 /tmp/d/hi/b.txt
    dr-------- z        z                4096 /tmp/d/nope
    Error(Cannot explore /tmp/d/nope: permission denied)
    drwxr-xr-x jao      jao              4096 /tmp/d/welcome
    -rw-r--r-- jao      jao                 0 /tmp/d/welcome/c.txt
    -rw-r--r-- jao      jao                 0 /tmp/d/welcome/d.txt
```

Notice that the nope directory is listed as before, but we get an error on the attempt
to go inside of it. The error indicates when the attempt was made -- between listing
the `hi` and `welcome` directories.

Normal output from this command comprises tuples of size 1, each containing a `File` object. The error
is carried by an `Error` object. Filtering can be performed to separate out normal and error 
output when desired.

Licensing
---------

The predecessor project ([osh](https://github.com/geophile.osh)) was
GPL. I've removed those headers, and will revisit the license issue,
but there will be no restrictions on the use of this software.

Status
------

This is pretty rudimentary so far. There is no installation script, no documentation (other than this
README, and comments in the code), and lots of features and commands are missing.
Marcel is obviously not ready to be the shell I would use routinely. If you want to try it out, 
use a script
like this:

```
    #!/bin/bash

    MARCEL_HOME=~/git/marcel/src
    MARCEL_MAIN=$MARCEL_HOME/marcel/main.py

    PYTHONPATH=$MARCEL_HOME

    python3 $MARCEL_MAIN
```

If you want examples of marcel usage, take a look at `test/test_execution.py`.
