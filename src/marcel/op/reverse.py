import marcel.core


SUMMARY = '''
The input stream is output in reverse order.
'''


DETAILS = None


def reverse():
    return Reverse()


class ReverseArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('reverse', env, None, SUMMARY, DETAILS)


class Reverse(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.contents = []

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass
    
    def receive(self, x):
        self.contents.append(x)
    
    def receive_complete(self):
        self.contents.reverse()
        for x in self.contents:
            self.send(x)
        self.send_complete()
