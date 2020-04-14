import signal
import time


def handler(x, frame):
    print(f'Caught {signal.Signals(x).name}')


signal.signal(signal.SIGINT, handler)  # ctrl-c
signal.signal(signal.SIGQUIT, handler)  # ctrl-d
signal.signal(signal.SIGTSTP, handler)  # ctrl-z

count = 0
while True:
    try:
        time.sleep(2)
    except KeyboardInterrupt:
        print(f'Caught KeyboardInterrupt on cycle {count}')
    print(f'cycles: {count}')
    count += 1
