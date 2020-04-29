HELP = '''
Several marcel operators take function arguments. These functions 
run in a namespace maintained by marcel. This namespace contains
the equivalent of environment variables from other shells. For example,
there are {n:USER} and {n:PWD} variables, which contain the values of
the user and the current directory.

Marcel is configured by running the configuration file
{n:~/.marcel.py} on startup. This script operates on the marcel
namespace, allowing you to customize the prompt, the color scheme used
for output, database and remote host login configuration, as well as
defining any other symbols you would like to have available. As usual,
these symbols can be defined by imports, by assigning variables, and
by defining functions and classes.

For more detail on configuration run {n:help} on the following topics:

{L}- {n:color}: Customizing the color scheme.
{L}- {n:prompt}: Customizing the prompt.
{L}- {n:namespace}: Adding symbols to the marcel namespace.
'''
