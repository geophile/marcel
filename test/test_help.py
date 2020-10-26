import marcel.helpformatter


class TestColorScheme:

    def __init__(self):
        self.help_reference = 'R'
        self.help_bold = 'B'
        self.help_italic = 'I'
        self.help_name = 'N'
        self.help_color = 'C'

    def bold(self):
        return 1

    def italic(self):
        return 2

    def color(self, r, g, b, style):
        return f'C{r}{g}{b}{"" if style == 0 else "b" if style == 1 else "i" if style == 2 else "bi"}'


def colorize(text, color):
    return f'({color}:{text})'


color_scheme = TestColorScheme()
formatter = marcel.helpformatter.HelpFormatter(color_scheme, colorize)

text = '''
{L,wrap=F}out [-a|--append FILENAME] [-f|--file FILENAME] [-c|--csv] [-p|--pickle] [FORMAT]

{L,indent=4:28}{r:-a}, {r:--append}            Append output to the file identified by FILENAME.

{L,indent=4:28}{r:-f}, {r:--file}              Write output to the file identified by FILENAME, 
replacing an existing file if necessary.

{L,indent=4:28}{r:-c}, {r:--csv}               Format output as comma-separated values.

{L,indent=4:28}{r:-p}, {r:--pickle}            Pickle the output.

{L,indent=4:28}{r:FORMAT}                  The Python formatting specification to be applied to output tuples.


Tuples arriving on the input stream are formatted and written out to a file (or stdout). 

Tuples received on the input stream are passed to the output stream. As a side-effect, input
tuples are formatted and written to stdout or to the specified {r:FILENAME}. 
If the {r:FILENAME} is specified
by {r:--file}, then an existing file is replaced. If the {r:FILENAME} is specified
by {r:--append}, then output is appended to an existing file.

The {r:--append} and {r:--file} options are mutually exclusive.

The formatting options: {r:--csv}, {r:--pickle}, and {r:FORMAT} options are mutually exclusive.
If no formatting options are specified, then the default rendering is used, except
that 1-tuples are unwrapped. (Note that for certain objects, including
{r:File} and {r:Process}, the default rendering is specified by the {n:render_compact()}
or {n:render_full()} methods. Run {n:help object} for more information.)
If the {r:--pickle} formatting option is specified, then output must go to a file, i.e.
{r:--file} or {r:--append} must be specified.

{n:Error} objects are not subject to formatting specifications, and are not passed on as output.
'''


def plain_and_formatted(label, text):
    print(f'{label}: ORIGINAL')
    print(text)
    print(f'{label}: FORMATTED')
    print(formatter.format(text))
    print('-----------------------------------------------------------------------------')


plain_and_formatted('text', text)
