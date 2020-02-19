Marcel
======

Marcel is a shell. The main idea is to rely on piping as the primary
means of building up functionality, as with any Unix or Linux
shell. However, instead of passing strings from one command to the
next, marcel passes Python objects: builtin types such as lists,
tuples, strings, and numbers; but also objects representing files and
processes.

Marcel is the success to [osh](http://github.com/geophile/osh) (Object SHell). Osh
is based on the same ideas, but it is not a full-fledged shell; it is an executable
that takes shell-like commands as input, composes using pipes, and passes Python objects,
as Marcel does. Marcel improves on osh in a number of ways:

* It is a full-fledged shell.
* Completely configured in Python. E.g., colorization and the prompt can be specified in Python code.
* Pipelines are supported as first-class constructs, allowing for more complex commands 
(using multiple pipelines), and the composition of pipelines.
* A number of ugly hacks in osh are done in more Pythonic ways in marcel.

Example
-------
You can locate Python processes as follows:

    M jao@cheese:~$ ps | select (p: p.commandline.startswith('/usr/bin/python')) 
      921 /usr/bin/python3 /usr/lib/system76-driver/system76-daemon
      933 /usr/bin/python3 /usr/bin/networkd-dispatcher --run-startup-triggers
     2228 /usr/bin/python3 /usr/lib/hidpi-daemon/hidpi-daemon
     2295 /usr/bin/python3 /usr/lib/hidpi-daemon/hidpi-notification

* `ps`: Generates a stream of `Process` objects.

* `|`: Pipes the `Process`es to the next command.

* `select (p: ...)`: Selects `Process`es, `p`, for which the
condition is true. This condition, which is written in Python, returns
`True` for a `Process` `p` whose commandline starts with
`'/usr/bin/python'`.

* The output renders each qualifying `Process` using formatting
(including colorization) specified as part of the implementation of
the `Process` object.

Another Example
---------------
You can find all files recursively, and then find the sum of file sizes by extension as follows:

    M jao@cheese:~/git/osh2$ ls -fr | map (f: (f.path.suffix, 1, f.size)) | red . + +
    ('.xml', 5, 28176)
    ('.iml', 1, 819)
    ('.py', 59, 146934)
    ('.txt', 12, 20814)
    ('', 646, 596689)
    ('.sample', 11, 18844)
    ('.pyc', 43, 129403)
    ('.md', 1, 1378)
    
* `ls -fr`: List just files (`-f`) recursively (`-r`).

* `map(f: (f.path.suffix, 1, f.size))`: Map each file, `f`, to a tuple containing the file's 
extension, 1, and the file size.

* `red . + +`: Reduce the incoming stream, grouping by the first part of each tuple, denoted 
by `.`, (the extension), and summing up the `1`s (to obtain the count for that extension), 
and the sizes.

Errors
------
The model of `stdout` and `stderr` streams is necessary to distinguish normal output from errors.
An unfortunate aspect of this approach is that the interleaving of normal output and errors is lost.
A marcel pipeline generates a stream of values, and each value has a type. This allows for normal
and error output to be combined in one stream, since error values can be identified by type.

For example, 