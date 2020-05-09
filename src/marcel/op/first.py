import marcel.op.apiop


def _first(output, unwrap_singleton, errors, error_handler):
    return First(output, unwrap_singleton, errors, error_handler)


class First(marcel.op.apiop.APIOp):

    def __init__(self, output, unwrap_singleton, errors, error_handler):
        super().__init__(output, unwrap_singleton, errors, error_handler, True)
