import marcel.core
import marcel.exception


# errors is None, error_handler is None: Errors go into output
# errors it not None: error_handler must be None, Errors go into errors
# error_handler is not None: errors mus be None, call error_handler on each Error
def gather(unwrap_singleton, output, errors=None, error_handler=None, stop_after_first=False):
    def error_to_output(env, error):
        output.append(error)

    def error_to_errors(env, error):
        errors.append(error)

    op = Gather()
    op.unwrap_singleton = unwrap_singleton
    op.output = output
    op.stop_after_first = stop_after_first
    if errors is None and error_handler is None:
        op.error_handler = error_to_output
    elif errors is not None:
        assert error_handler is None
        op.error_handler = error_to_errors
    elif error_handler is not None:
        assert errors is None
        op.error_handler = error_handler
    return op


class Gather(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.unwrap_singleton = None
        self.output = None
        self.error_handler = None

    def __repr__(self):
        return f'gather()'

    # BaseOp
    
    def doc(self):
        return None

    def setup_1(self):
        pass

    def receive(self, x):
        if self.unwrap_singleton and len(x) == 1:
            x = x[0]
        self.output.append(x)
        raise marcel.exception.KillCommandAfterFirstException()

    def receive_error(self, error):
        self.error_handler(self.owner.env, error)
        raise marcel.exception.KillCommandAfterFirstException()
