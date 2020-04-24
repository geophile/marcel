HELP = '''
b{Relationship to Python:}

b{Commands:}

Marcel commands include builtin i{operators}, and i{executables} from the host operating system.
They can be combined arbitrarily using pipes. Executables always take strings as input,
and yield strings as output. Builtin operations may do that to, but some operations pipe
other Python types too. An example:

i{List the names of users whose shell is /bin/bash:}

The file n{/etc/passwd} contains usernames and shell executables.
n{cat}, n{xargs}, and n{echo} are Linux executables. n{map} and
n{select} are marcel operators. The output is condensed into one line
through the use of xargs and echo.

    cat /etc/passwd | \\
    map (line: line.split(':')) | \\
    select (*line: line[-1] == '/bin/bash') | \\
    map (*line: line[0]) | \\
    xargs echo

Comments:

    - {cat /etc/passwd}: Write each line of {/etc/passwd} to the output stream,

    - {map (line: line.split(':'))}: Split the lines at the {:} separators, yielding 7-tuples.

    - {select (*line: line[-1] == '/bin/bash')}: Select those lines in which the last field is 
      {/bin/bash}.

    - {map (*line: line[0])}: Keep the username field of each input tuple.

    - {xargs echo}: Combine the incoming usernames into a single line, which is printed to n{stdout}.

    - {\\}: A line terminating in {\\} indicates that the command continues on the next line.

For more information on commands, do n{help commands}.

b{Pipelines:}

A i{pipeline} is a sequence of commands combined by pipes, as in the example above. 

A pipeline is sometimes bracketed using n{[...]} when the pipeline is
part of another command. For example, this command lists the sum of file sizes under 
n{/tmp}:

    ls -fr /tmp | map (f: f.size) | red +

To run this command on a remote host named n{fred}:

    @fred [ ls -fr /tmp | map (f: f.size) | red + ]

Comments:

    - {@fred}: The name {fred} has been configured to refer to some host, and to provide
      login credentials.

    - {[...]}: The command to be executed on {fred} is delimited by {[...]}

    - The output includes the name of the host on which the command executed, e.g.

      (fred, 1366422)

Of course, the summation could done remotely, by returning the file sizes, and
then doing the summation locally:

    @fred [ ls -fr /tmp ] | map (host, file: file.size) | red +

Comments:

    - The remote command returns (host, n{File}) tuples.

    - {map (host, file: file.size)}: Discard the host information, and extract the size
      of the n{File}. (The file was captured remotely and returned with the n{File} object.)

b{Configuration:}


b{Environment:}
'''
