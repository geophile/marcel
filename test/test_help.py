import marcel.helpformatter
import marcel.object.color

text = '''
This is a line.
This is another line.
This line contains a {flag}.
Here is i{italic} and b{bold} text, and a n{name}.


    this is code
    so is this, witn a n{name}
'''

color_scheme = marcel.object.color.ColorScheme()
color_scheme.help_highlight = 'H'
color_scheme.help_bold = 'B'
color_scheme.help_italic = 'I'
color_scheme.help_name = 'N'


def format(text, color):
    return f'{color}({text})'


def dump(help):
    for block in help.blocks:
        print(block)
        if isinstance(block, marcel.helpformatter.Paragraph) and block.markup and len(block.markup) > 0:
            print('        MARKUP {')
            for markup in block.markup:
                print(f'        {markup}')
            print('        }')
            if block.plaintext:
                print('        PLAINTEXT {')
                print(block.plaintext)
                print('        }')
            if block.wrapped:
                print('        WRAPPED {')
                print(block.wrapped)
                print('        }')


help = marcel.helpformatter.HelpFormatter(color_scheme, format)
formatted = help.format(text)
# dump(help)
print(formatted)
