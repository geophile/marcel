HELP = '''
Several marcel operators rely on i{functions}. For example, you can
list n{.mp3} files anywhere inside your home directory as follows:

    ls -fr ~ | select (lambda f: f.suffix.lower() == '.mp3')

{ls -fr ~} lists files only ({-f}), recursively ({-r}), starting with
the home directory ({~}). The {ls} command yields n{File} objects
which are then piped to the {select} operator.

{select} has a function, delimited by parentheses. This function binds
each n{File} arriving on the input stream, to the parameter {f}. The
function returns n{True} if the n{File}'s suffix is n{.mp3}, n{False}
otherwise. n{File} objects support the n{pathlib.Path} interface, so
{f.suffix} returns the extension of n{File} {f}, (including the
dot). Then, {.lower()} converts the extension to lower case, and the
resulting string is compared to {.mp3}.

All marcel operators that rely on functions use the same syntax demonstrated 
here: The function is enclosed in parentheses; the parameters are bound
to components of incoming tuples. And in all cases, the n{lambda} keyword
can be omitted.
'''
