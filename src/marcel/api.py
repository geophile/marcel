import marcel.core
import marcel.function
import marcel.op.gen
import marcel.op.ls
import marcel.op.map
import marcel.op.out
import marcel.main


MAIN = marcel.main.Main(op_testing=True)


def gen(count=0, start=0, pad=None):
    op = marcel.op.gen.Gen()
    op.count = count
    op.start = start
    op.pad = pad
    return op


def out(append=None, file=None, csv=False, format=None):
    op = marcel.op.out.Out()
    op.append = append
    op.file = file
    op.csv = csv
    op.format = format
    return op


def ls(*paths, depth=1, recursive=False, file=False, dir=False, symlink=False):
    op = marcel.op.ls.Ls()
    op.d0 = depth == 0
    op.d1 = depth == 1
    op.recursive = recursive
    op.file = file
    op.dir = dir
    op.symlink = symlink
    op.filename = paths
    return op


def map(function):
    op = marcel.op.map.Map()
    op.function = marcel.function.Function('', MAIN.env.namespace, f=function)
    return op


def execute(pipeline):
    if isinstance(pipeline, marcel.core.Op):
        op = pipeline
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
    MAIN.run_api(pipeline)


class I:

    def __init__(self, output):
        self.output = output
        self.i = None

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.output):
            next = self.output[self.i]
            self.i += 1
            return next
        else:
            raise StopIteration()


def loop(pipeline):
    output = []
    def gather(x):
        output.append(x)
    if isinstance(pipeline, marcel.core.Op):
        op = pipeline
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
    pipeline.append(map(gather))
    MAIN.run_api(pipeline)
    return I(output)
