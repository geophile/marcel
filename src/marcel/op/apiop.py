import marcel.core
import marcel.exception


class APIOp(marcel.core.Op):

    def __init__(self, output, unwrap_singleton, errors, error_handler, stop_after_first):
        super().__init__()
        self.unwrap_singleton = unwrap_singleton
        self.stop_after_first = stop_after_first
        self.output = output
        self.errors = errors
        self.error_handler = (self.error_to_output if errors is None and error_handler is None else
                              self.error_to_errors if errors is not None and error_handler is None else
                              error_handler if errors is None and error_handler is not None else
                              None)  # indicates incorrect use of errors and error_handler args

    # BaseOp

    def doc(self):
        return None

    def setup_1(self):
        self.check_arg(self.error_handler is not None,
                       None,
                       'Specify at most one of the errors and error_handler arguments.')

    def receive(self, x):
        if self.unwrap_singleton and len(x) == 1:
            x = x[0]
        self.output.append(x)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    def receive_error(self, error):
        self.error_handler(self.owner.env, error)
        if self.stop_after_first:
            marcel.exception.StopAfterFirst()

    # For use by this class

    def error_to_output(self, env, error):
        self.output.append(error)

    def error_to_errors(self, env, error):
        self.errors.append(error)
