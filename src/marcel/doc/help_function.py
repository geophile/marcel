HELP = '''
Several marcel operators rely on {i:functions}. For example, you can
list {n:.mp3} files anywhere inside your home directory as follows:

{p,wrap=F}
    ls -fr ~ | select (lambda f: f.suffix.lower() == '.mp3')

{r:ls -fr ~} lists files only ({r:-f}), recursively ({r:-r}), starting with
the home directory ({r:~}). The {r:ls} command yields {n:File} objects
which are then piped to the {r:select} operator.

{r:select} has a function, delimited by parentheses. This function binds
each {n:File} arriving on the input stream, to the parameter {r:f}. The
function returns {n:True} if the {n:File}'s suffix is {n:.mp3}, {n:False}
otherwise. {n:File} objects support the {n:pathlib.Path} interface, so
{r:f.suffix} returns the extension of {n:File} {r:f}, (including the
dot). Then, {r:.lower()} converts the extension to lower case, and the
resulting string is compared to {r:.mp3}.

All marcel operators that rely on functions use the same syntax demonstrated 
here: The function is enclosed in parentheses; the parameters are bound
to components of incoming tuples. And in all cases, the {n:lambda} keyword
can be omitted.
'''
