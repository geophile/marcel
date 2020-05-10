Marcel
======

[Marcel is a shell](https://www.youtube.com/watch?v=VF9-sEbqDvU). 
The main idea is to rely on piping as the primary
means of building up functionality, as with any Unix or Linux
shell. However, instead of passing strings from one command to the
next, marcel passes Python objects: builtin types such as lists,
tuples, strings, and numbers; but also objects representing files and
processes.

Linux has extremely powerful commands such as `awk` and `find`.
Most people know how to do a few simple operations using these commands,
but cannot fully exploit them due to their reliance on extensive "sublanguages".  By 
contrast, if you know Python, then you already know the language used by marcel.
Python expressions, combined with marcel operators, allow you to do much of what can
be done relying on the more obscure corners of `awk` and `find`.

Shells are intended for interactive usage, from a console. A script
is created by putting commands into a text file, and setting the executable
bits. This means that the shell language must include control constructs,
functions, variables, and so on.  
Marcel takes a different approach. Because marcel is based on Python,
there is no need to invent a new language. 
Instead, you can use Python as the scripting language, invoking
marcel commands via an API, (more on this below).

Marcel is the successor to [osh](http://github.com/geophile/osh) 
(Object SHell). Osh
is based on the same ideas, but it is not a full-fledged shell;
it is an executable
that takes shell-like commands as input, composes them using pipes, 
and passes Python objects,
as Marcel does. Marcel improves on osh in a number of ways:

* Marcel is a full-fledged shell.

* If you know Python you know marcel. There are no obscure sublanguages
(e.g. for awk, find, PS1). Commands are customized by writing Python
lambda expressions on the command line. Configuration is done
by assigning Python variables.

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

* Extensive help facility, providing information on concepts, objects,
and commands.

* Customizable highlighted output of file and process listings.

* Context-sensitive tab completion (for commands, their flags, 
filenames, help topics).

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
Find all files recursively, summing the file count and file size for each file extension,
and then sort by decreasing size and report the top 10.
```
ls -fr \
| select (f: f.path.suffix != '') \
| map (f: (f.path.suffix.lower(), 1, f.size)) \
| red . + + \
| sort (ext, count, size: -size) \
| head 10

('.jpg', 82477, 63041371455)
('.mp3', 3492, 25752416039)
('.avi', 225, 19301810684)
('.m4a', 1251, 9798087657)
('.log', 630, 9425357624)
('.jar', 5202, 7111116450)
('.m4v', 5, 4462527594)
('.csv', 1418, 4094816065)
('.mkv', 1, 3195052033)
('.pack', 179, 2969390041)
```

* The command is broken up across a few lines using a \ at the end of each non-terminal line.

* `ls -fr`: List just files (`-f`) recursively (`-r`).

* `select (f: f.path.suffix != '')`: For each file, `f`, keep those for which the file's
extension (`f.path.suffix`) is not the empty string. The syntax inside the parentheses
is a Python function, (marcel permits omission of the `lambda` keyword).

* `map(f: (f.path.suffix.lower(), 1, f.size))`: Map each file, `f`, to a tuple containing 
the file's extension (folded to lower case), the integer 1, and the file size.

* `red . + +`: Reduce the incoming stream, grouping by the file extensions (in the tuple position 
identified by
the `.`), and summing up the `1`s (to obtain the count for that extension), 
and the sizes.

* `sort (ext, count, size: -size)`: Sort the incoming (extension, count, size) tuples
by decreasing size. 

* `head 10`: Keep the first 10 input tuples and discard the rest.

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

```
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

Scripting
---------

The second example above listed files recursively, summed the 
file count and file size for each file extension,
and then sorted by decreasing size, and reported the top 10:

```
    ls -fr \
    | select (f: f.path.suffix != '') \
    | map (f: (f.path.suffix.lower(), 1, f.size)) \
    | red . + + \
    | sort (ext, count, size: -size) \
    | head 10
```

To implement this as a Python script:
```
    #!/usr/bin/python3
    from marcel.api import *
    
    run(ls('.', file=True, recursive=True)
        | select(lambda f: f.path.suffix != '')
        | map(lambda f: (f.path.suffix.lower(), 1, f.size))
        | red(None, r_plus, r_plus)
        | sort(lambda ext, count, size: -size)
        | head(10))
```
Each marcel operator is invoked via a function imported from `marcel.api`.
For example, the console command `ls -fr` turns into `ls(file=True, recursive=True)`.
Piping uses the same symbol as on the console, `|`. The 
command pipeline is executed by calling `run`.

If instead of printing the results you want to manipulate them further,
use the pipeline as an iterator:

```
    #!/usr/bin/python3
    from marcel.api import *

    for ext, count, size in (ls('.', file=True, recursive=True)
                             | select(lambda f: f.path.suffix != '')
                             | map(lambda f: (f.path.suffix.lower(), 1, f.size))
                             | red(None, r_plus, r_plus)
                             | sort(lambda ext, count, size: -size)
                             | head(10))
        average = size / count
        print(f'{ext}: {average}')
```

Dependencies
------------

Marcel depends on [dill](https://pypi.org/project/dill/), which can be installed
like this:
```
python3 -m pip install dill
```

Installation
------------

Install using pip. To install to your home directory (e.g. under
`~/.local`):
```
python3 -m pip install marcel
```

Or to install for all users, e.g. in `/usr/local`:

```
sudo python3 -m pip install --prefix /usr/local marcel
```
