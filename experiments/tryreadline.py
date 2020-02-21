import readline

readline.parse_and_bind('set editing-mode emacs')

while True:
    line = input('> ')
    if line == 'exit':
        break
    print('RECEIVED: ' + line)
