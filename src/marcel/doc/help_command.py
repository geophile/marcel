HELP = '''
A marcel i{command} is a single action entered on the command line. There are
two types of commands:

    - b{Marcel operator:} A marcel operator is built into marcel. In its most 
      general form, an operator receives an input stream containing Python tuples,
      and writes an output stream containing Python tuples. Every marcel operator
      provides documentation via the help flags ({-h}, {--help}), or the {help}
      command. For more information on operators, run n{help operator}.

    - b{Linux executable:} Linux executables can be executed, as with any other
      shell. Many such executables can read and write streams of strings.

In some cases, the marcel operator has the same name as a Linux
executable with similar capabilities, e.g. n{ls}. This is intentional,
as the Linux executable operates in ways incompatible with
marcel. (The Linux executable can still be executed by using the
n{bash} command, e.g. {bash ls}.)

Operators and executables can be mixed freely. For example, here is a
command sequence that lists the names of users whose shell is
n{/bin/bash}. 

    cat /etc/passwd | \\
    map (line: line.split(':')) | \\
    select (*line: line[-1] == '/bin/bash') | \\
    map (*line: line[0]) | \\
    xargs echo

The file n{/etc/passwd} contains usernames and shell
executables. This file is written to n{stdout} by using
the Linux executable n{cat}. n{stdout} then feeds into a sequence of
three marcel operators ({map}, {select}, and then {map} again), and the
output from these operators feeds into another Linux executable, {xargs}, which
uses invokes {echo}.

Comments:

    - {cat /etc/passwd}: Write each line of {/etc/passwd} to the output stream,

    - {map (line: line.split(':'))}: Split the lines at the {:} separators, yielding 7-tuples.

    - {select (*line: line[-1] == '/bin/bash')}: Select those lines in which the last field is 
      {/bin/bash}.

    - {map (*line: line[0])}: Keep the username field of each input tuple.

    - {xargs echo}: Combine the incoming usernames into a single line, which is printed to n{stdout}.

    - {\\}: A line terminating in {\\} indicates that the command continues on the next line.
'''
