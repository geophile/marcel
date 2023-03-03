# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import marcel.argsparser
import marcel.core
import marcel.exception


HELP = '''
{L,wrap=F}tee PIPELINE ...

{L,indent=4:28}{r:PIPELINE}                Each {r:PIPELINE} receives the contents of the input stream. 

Tuples arriving in the input stream are passed to each {r:PIPELINE} and to the output stream.
'''


def tee(env, *pipeline):
    return Tee(env), [p.create_pipeline() for p in pipeline]


class TeeArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('tee', env)
        self.add_anon_list('pipelines', convert=self.check_str_or_pipeline, target='pipelines_arg')
        self.validate()


class Tee(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.pipelines_arg = None
        self.pipelines = None

    def __repr__(self):
        pipelines = [str(p) for p in self.pipelines]
        return f'{self.op_name()} {pipelines}'

    # AbstractOp

    def setup(self):
        if len(self.pipelines_arg) == 0:
            raise marcel.exception.KillCommandException('No pipelines given.')
        self.pipelines = []
        for pipeline in self.pipelines_arg:
            pipeline = marcel.core.PipelineWrapper.create(self.env(),
                                                          self.owner.error_handler,
                                                          pipeline,
                                                          lambda pipeline: pipeline)
            pipeline.setup()
            pipeline.prepare_to_receive()
            self.pipelines.append(pipeline)

    def receive(self, x):
        for pipeline in self.pipelines:
            pipeline.receive(x)
        self.send(x)

    def flush(self):
        for pipeline in self.pipelines:
            pipeline.flush()
        self.propagate_flush()

    def cleanup(self):
        for pipeline in self.pipelines:
            pipeline.cleanup()
