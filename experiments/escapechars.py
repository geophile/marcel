x = '\0331m[38;5;25m hello world \0330m'
print('<%s> %s' % (x, (len(x))))

x = '\[\0331m[38;5;25m\] hello world \[\0330m\]'
print('<%s> %s' % (x, (len(x))))
