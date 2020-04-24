HELP = '''
Marcel is a shell. Like any Linux shell, there are commands which
can be executed. These commands include both Linux executables (e.g. grep),
and marcel operators. In some cases, the marcel operator has the same name
as a Linux executable with similar capabilities, e.g. n{ls}. This is intentional,
as the Linux executable operates in ways incompatible with marcel. (The Linux
executable can still be executed by using the n{bash} command, e.g. {bash ls}.)

In marcel, as in other Linux shells, the output from one command can
be piped to another.  The conventional syntax is used, {|}. Linux
pipes stream unstructured text between commands. In marcel, streams
carry arbitrary Python objects.

Marcel is implemented in, and based on the Python language. Whereas
other shells invent new languages for control constructs, expressions,
and so on, marcel simply relies on Python. So the {map} operator takes
a stream of Python objects as input, and generates a stream of Python
objects as output. Each output object is computed by applying a Python
function to each input object. For example, this marcel code generates
a sequence of 100 integers, 0 through 99, and, outputs the each number
along with its square root:

    gen 100 | map (lambda x: (x, x**0.5))

Note that the Python function, mapping {x} to the tuple {(x, x**0.5)}
is enclosed in parentheses, as is the case whenever a function is
required. Marcel permits the n{lambda} keyword to be omitted.

The following topics will explain these concepts in more detail:

    - n{operator}
    - n{executable}
    - n{function}
    - n{pipeline}
'''
