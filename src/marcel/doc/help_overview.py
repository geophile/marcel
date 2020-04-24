HELP = '''
Marcel is a shell. Like any Linux shell, there are commands which
can be executed.  In fact, you can run a Linux shell command or
executable from marcel. Also, as in other shells, you can pipe the
output from one command into the input of another.  For example, you
can list .mp3 files anywhere inside your home directory, and sum their
sizes, as follows:

    ls -fr ~ | select (f: f.suffix.lower() == '.mp3') | map (f: f.size) | red +

This works as follows:

    - {ls -fr ~}: List files only ({-f}), recursively ({-r}), in the home directory ({~}).

    - {|}: Pipe the n{File} objects resulting from {ls} to the next command.
 
    - {select (...)}: {select} is the marcel operator for filtering items in a stream.
      The selection predicate, inside the parentheses, is a Python expression, (although
      you can omit the n{lambda} keyword). The parameter {f} is bound to a n{File}
      piped in from the {ls} command. The predicate extracts the extension of the n{File}
      (using the n{pathlib.Path.suffix} method), converts to lower case, and then compares
      to n{.mp3}.

    - {map (...)}: The qualifying n{File}s are piped to the {map} command, which applies
      a function to each incoming item. In this case, the function extracts the size
      of the file.

    - {red +}: The file sizes are piped to the reduction command, {red}. The reduction
      is done by applying {+} repeatedly, to the incoming sizes.

Use n{help} to get more information on:

    - n{concepts}: The major concepts you need to understand to use marcel.

    - n{commands}: To get a list of marcel commands.

    - n{objects}: To get a list of builtin objects.

'''
