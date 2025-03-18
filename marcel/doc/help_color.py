# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

HELP = '''
Marcel uses a {i:color scheme} to colorize the prompt and other items printed
on the console. 

{b:Color:}

{r:Color} is an object type built in to marcel. A {r:Color} is
created by providing RGB values, and style specifications {n:BOLD}
and/or {n:ITALIC}. Colors are typically assigned to variables
in your configuration script, (run
{n:help configuration} for more information on configuration). Example:

{p,wrap=F,indent=4}
WHITE = Color(5, 5, 5)
RED_BOLD = Color(5, 0, 0, BOLD)
DARK_GREY_BOLD_ITALIC = Color(2, 2, 2, BOLD | ITALIC)

The RGB values are in the range 0-5, which make for a 6 f 6 f 6 color cube.
These values are used to define an ANSI escape
sequence. 

{r:Color}s have two purposes:
{L,indent=4:7}1. They can be used to customize the console prompt, (run {n:help prompt}
   for more information).
{L,indent=4:7}2. They can be used to define a color scheme, to colorize various output items,
   (discussed next).

{b:Color scheme:}

A {i:color scheme} is a set of color specifications, used by marcel to 
display various items. The marcel namespace contains the {r:COLOR_SCHEME} variable
which is bound to an object of type {n:ColorScheme}. {n:ColorScheme} has a number of
keys which can be assigned colors. Example:

{p,wrap=F,indent=4}
COLOR_SCHEME.file_file = COLOR_WHITE_BOLD
COLOR_SCHEME.file_dir = Color(0, 2, 3, BOLD)
COLOR_SCHEME.file_link = Color(4, 2, 0, BOLD)
COLOR_SCHEME.file_executable = Color(0, 4, 0, BOLD)
COLOR_SCHEME.file_extension =  \\{'.jpg': COLOR_IMAGE_HIGHLIGHT,
                                '.jpeg': COLOR_IMAGE_HIGHLIGHT,
                                '.png': COLOR_IMAGE_HIGHLIGHT,
                                '.mov': COLOR_IMAGE_HIGHLIGHT,
                                '.avi': COLOR_IMAGE_HIGHLIGHT,
                                '.gif': COLOR_IMAGE_HIGHLIGHT\\}
COLOR_SCHEME.error = Color(5, 5, 0)
COLOR_SCHEME.process_pid = Color(0, 2, 4, BOLD)
COLOR_SCHEME.process_command = Color(3, 2, 0, BOLD)
COLOR_SCHEME.help_reference = Color(5, 3, 0)
COLOR_SCHEME.help_bold = COLOR_DOC_BOLD
COLOR_SCHEME.help_italic = COLOR_DOC_ITALIC
COLOR_SCHEME.help_name = Color(3, 3, 5)

Notes:

{L}- The {r:file_...} entries control how {n:File} objects are displayed in a
     detailed listing (e.g., obtained by the {n:ls} operator. Run 
     {n:help object} for more information on how builtin objects are 
     displayed and colorized).
{L}- The {r:COLOR_SCHEME.file_extension} key is bound to a Python dict which maps
     file extensions to colors. 
{L}- {r:error} is the color used for printing {n:Error} objects by the {n:out} operator.
{L}- {r:process_...} entries control the display of {n:Process} objects.
{L}- {r:help_...} entries control colorization of {n:help} text, (like the text you are 
     reading right now).
{L}- A {n:Color} can be constructed, or assigned from a variable.

'''
