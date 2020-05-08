import marcel.op.apiop


def _gather(output=[], unwrap_singleton=True, errors=None, error_handler=None):
    return Gather(output, unwrap_singleton, errors, error_handler)


class Gather(marcel.op.apiop.APIOp):

    def __init__(self, output, unwrap_singleton, errors, error_handler):
        super().__init__(output, unwrap_singleton, errors, error_handler, False)

    def __repr__(self):
        return f'gather()'

    # BaseOp
    
    def doc(self):
        return None
