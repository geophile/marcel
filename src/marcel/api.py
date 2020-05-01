import marcel.core
import marcel.functionwrapper
import marcel.op
import marcel.main

from marcel.op.gen import gen
from marcel.op.ls import ls
from marcel.op.map import map

MAIN = marcel.main.Main(op_testing=True)


def execute(pipeline):
    if isinstance(pipeline, marcel.core.Op):
        op = pipeline
        pipeline = marcel.core.Pipeline()
        pipeline.append(op)
    MAIN.run_api(pipeline)
