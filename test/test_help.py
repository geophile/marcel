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
{p}This text
should be wrapped.
{p,wrap=T}This text should
also be wrapped.
{p,wrap=F}This
    text
    should
    not 
    be 
    wrapped
'''

HELP = '''
To learn more about a topic, run the command:

    help TOPIC

Available topics:

{b:Top-level help:}
{p,wrap=F}
    - {n:marcel}

(Or just run {n:help} with no topic.)

{b:Overview:}
{p,wrap=F}
    - {n:configuration}: How to configure the prompt, color scheme, remote access.
    - {n:overview}: The main concepts of marcel. How it differs from other shells.
    - {n:interaction}: Interacting with marcel.
    - {n:command}: Marcel operators, Linux executables.
    - {n:function}: Several operators rely on Python functions.
    - {n:pipeline}: Structuring commands into sequences, using pipes.
    - {n:object}: The objects you work with. 

{b:Objects}:
{p,wrap=F}
    - {n:file}
    - {n:process}

{b:Operators:}
{p,wrap=F}
    - {n:bash}        - {n:bg}          - {n:cd}
    - {n:dirs}        - {n:edit}        - {n:expand}
    - {n:fg}          - {n:gen}         - {n:head}
    - {n:help}        - {n:jobs}        - {n:ls}
    - {n:map}         - {n:out}         - {n:popd}
    - {n:ps}          - {n:pushd}       - {n:pwd}
    - {n:red}         - {n:reverse}     - {n:select}
    - {n:sort}        - {n:squish}      - {n:sudo}
    - {n:tail}        - {n:timer}       - {n:unique}
    - {n:version}     - {n:window}
'''

text = HELP

print(f'ORIGINAL: {text}')
formatted = formatter.format(text)
print(f'FORMATTED: {formatted}')
