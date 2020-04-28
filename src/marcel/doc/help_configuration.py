HELP = '''
Marcel is configured with a Python script executed on startup: {n:~/.marcel.py}.
In this file, you can use functions provided by marcel to customize your 
environment, and to record configuration information for various resources
you need to access, such as remote hosts and databases.
Furhtermore, any symbols that you define or import are made available to the execution
of all commands. 

In other words, the configuration script runs in a namespace which provides 
a number of functions you can invoke to configure marcel, and you can add symbols
to the namespace for future use.

{b:Customizing the prompt:}

The default marcel prompt is {n:$}. 
You can customize the prompt by calling {n:define_prompt} function 
in the configuration script. For example:
{p,wrap=F}
    define_prompt([
        RED_BOLD,
        'M ',
        Color(0, 2, 1, bold=True),
        USER,
        '@',
        HOST,
        WHITE,
        ':',
        Color(0, 3, 3, BOLD),
        lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD,
        '$ '])

This produces the following prompt:
{p,wrap=F}
    {c500b:M} jao@cheese:~$

(The {c500b:M} is there to remind me, while developing marcel, that I am
running marcel, not bash.)

The list passed to {n:define_prompt} contains a number of elements that
are evaluated each time a prompt is displayed:
{p,wrap=F}
    - {r:RED_BOLD}: An environment variable bound to a {n:Color} object.
      This color will be used for displaying subsequent text.
{p,wrap=F}
    - {r:'M '}: Display the indicated string, colored {r:RED_BOLD}, as just noted.
{p,wrap=F}
    - {r:Color(0, 2, 1, bold=True)}: The following text is displayed in
      the indicated color, (and made bold).
{p,wrap=F}
    - {r:USER}: An environment variable, representing the currently logged in user.
      Evalutes to the variable's value.
{p,wrap=F}
    - {r:'@'}: The string {r:@}.
{p,wrap=F}
    - {r:HOST}: Another environment variable, the hostname of the host.
{p,wrap=F}
    - {r:WHITE}: Evaluates to a {n:Color}, to control subsequent text.
{p,wrap=F}
    - {r:':'}: The string {r::}.
{p,wrap=F}
    - {r:Color(0, 3, 3, BOLD)}: A {n:Color}.
{p,wrap=F}
    - {r:lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD}: 
      A function computing the rendering of the current directory. If the
      current directory, stored in the environment variable {r:PWD}, is under
      the {r:HOME} directory, then display a path starting with {r:~}. Otherwise
      print {r:PWD} as is. Because {r:PWD} changes over time, (as the user executes
      {n:cd}, {n:pushd}, and {n:popd} operations), the function is left unevaluated
      (hence the {n:lambda}). Marcel evalutes functions included in a prompt
      specification whenever the prompt needs to be displayed.
{p,wrap=F}
    - {r:'$ '}: The string {r:$}.

For multi-line commands, a second prompt can be defined by calling the
function {n:define_continuation_prompt}.

{b:Customizing the color scheme:}

Marcel uses 8-bit color, specified by ANSI escape sequences. This
specification employs a 6 x 6 x 6 color cube. A color can be specified
by using the {n:marcel.object.colorschema.Color} object. For example, 
{p,wrap=F}
    Color(3, 4, 5)

The first three arguments specify red, green, and blue color values,
between 0 and 5. An optional fourth argument can be used to specify
styling, with options {n:BOLD} and {n:ITALIC}. These can be combined
using the {n:|} operator, e.g.
{p,wrap=F}
    Color(5, 0, 0, BOLD | ITALIC)

A {i:color scheme} is a set of color specifications, used by marcel to 
display various items. The color schema used by marcel is defined by
the {n:define_color_scheme} function, e.g.
{p,wrap=F}
    define_color_scheme(file_file='white_bold',
                        file_dir=Color(0, 2, 3, bold=True),
                        file_link=Color(4, 2, 0, bold=True),
                        file_executable=Color(0, 4, 0, bold=True),
                        file_extension=((('.jpg': 'image_highlight',
                                        '.jpeg': 'image_highlight',
                                        '.png': 'image_highlight',
                                        '.gif': 'image_highlight'))),
                        error=Color(5, 5, 0),
                        process_pid=Color(0, 2, 4, bold=True),
                        process_commandline=Color(3, 2, 0, bold=True),
                        help_reference=Color(5, 3, 0),
                        help_bold='doc_bold',
                        help_italic='doc_italic',
                        help_name=Color(3, 3, 5))

Notes:
{p,wrap=F}
    - The {r:file_...} entries control how {n:File} objects are displayed in a
      detailed listing (e.g., obtained by the {n:ls} command. Run 
      {n:help object} for more information on how builtin objects are 
      displayed and colorized).
{p,wrap=F}
    - {r:error} is the color used for printing {n:Error} objects by the {n:out} command.
{p,wrap=F}
    - {r:process_...} entries control the display of {n:Process} objects.
{p,wrap=F}
    - {r:help_...} entries control colorization of {n:help} text.

{b:Imports:}

You can use marcel as a calculator, by using the {n:map} command,
specifying a function with no arguments.
{p,wrap=F}
    M jao@cheese:~$ map (5 + 7)
    12

To compute the golden ratio:
{p,wrap=F}
    M jao@cheese:~$ map ((1 + sqrt(5))/2)
    Error(map((1 + sqrt(5))/2) failed on : name 'sqrt' is not defined

This fails because {n:sqrt} is not a builtin function in Python. It comes from
the {n:math} module. If this line is added to {n:~/.marcel.py}:
{p,wrap=F}
    from math import sqrt

then {n:sqrt} can be used:
{p,wrap=F}
    M jao@cheese:~$ map ((1 + sqrt(5))/2)
    1.618033988749895

{b:Definitions:}

You can also define symbols in the usual way, assigning variables,
defining functions and classes. Any symbols you define will be available
in your marcel commands.

For example, if you put this code in your configuration script:
{p,wrap=F}
    import time
    def current_time():
        return time.asctime(time.gmtime())

Then you can use the {n:current_time} function in your commands, e.g.
{p,wrap=F}
    M jao@cheese:~$ timer 1 | map (t: (current_time(), t))
    ('Sat Apr 25 17:58:31 2020', 1587837511.0)
    ('Sat Apr 25 17:58:32 2020', 1587837512.0)
    ('Sat Apr 25 17:58:33 2020', 1587837513.0)
    ...
'''
