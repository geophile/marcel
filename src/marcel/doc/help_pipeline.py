HELP = '''
A i{pipeline} is a sequence of commands combined by pipes, as in the example above. 

A pipeline is bracketed using n{[...]} when the pipeline is
part of another command. For example, this command lists the sum of file sizes under 
n{/tmp}:

    ls -fr /tmp | map (f: f.size) | red +

To run this command on a remote host named n{fred}:

    @fred [ ls -fr /tmp | map (f: f.size) | red + ]

Comments:

    - {@fred}: The name {fred} has been configured to refer to some host, and to 
      provide login credentials. (For more information on configuration, run
      n{help configuration}.
      

    - {[...]}: The command to be executed on {fred} is delimited by {[...]}

    - The output includes the name of the host on which the command executed, e.g.

      n{(fred, 1366422)}

The summation could also done locally, by returning the file sizes, and
then doing the summation:

    @fred [ ls -fr /tmp ] | map (host, file: file.size) | red +

Comments:

    - The remote command returns (host, n{File}) tuples.

    - {map (host, file: file.size)}: This function discards the host information, 
      and extracts the size of the n{File}. (The file's size was captured remotely 
      and returned with the n{File} object.)
'''
