# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
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
import marcel.op.redirect
import marcel.pipeline

HELP = '''
{L,wrap=F}case PREDICATE (| PIPELINE |) ... [(| PIPELINE |)]

{L,indent=4:28}{r:PREDICATE}               Used to determine if an input tuple is passed to the next PIPELINE.

{L,indent=4:28}{r:PIPELINE}                A pipeline processing input tuples for which the preceding 
PREDICATE is true.

Input tuples are sent to at most one of the PIPELINEs, and output from
all the PIPELINEs is sent downstream.

An input tuple is evaluated by each {r:PREDICATE} in turn. For the first
{r:PREDICATE} evaluating to True, the input tuple is passed to the
{r:PIPELINE} following the {r:PREDICATE}. There may be one {r:PIPELINE} at the end
without a preceding {r:PREDICATE}. This is a default case: if a tuple
evaluates to False with each {r:PREDICATE}, then the tuple is passed to
this default {r:PIPELINE}. If there is no default {r:PIPELINE}, then a tuple
evaluating to False with all predicates will not be processed further.

All {r:PIPELINE} outputs feed into the output for this operator.

Example:

{L,indent=4,wrap=F}gen 100 1 | case \\\\
                 (f: f % 15 == 0) (| (f: (f, 'FizzBuzz')) |) \\\\
                 (f: f % 3 == 0)  (| (f: (f, 'Fizz')) |) \\\\
                 (f: f % 5 == 0)  (| (f: (f, 'Buzz')) |) \\\\
                                  (| (f: (f, f)) |)

This implements FizzBuzz. The integers 1 .. 100 are piped to the case
operator. The predicates test for divisibility by 15, 3, and 5. It is
important to handle divisibility by 15 first, since qualifying numbers are
also divisible by 3 and 5, and case executes the first {r:PIPELINE} whose
{r:PREDICATE} evaluates to True. The default pipeline handles numbers not
divisible by 3, 5, or 15.
'''


def case(*args):
    return Case(), args


class CaseArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('case', env)
        self.add_anon_list('args', convert=self.function_or_pipeline)
        self.validate()


class Case(marcel.core.Op):
    class Branch(object):

        def __init__(self, predicate, pipeline):
            self.predicate = predicate
            self.pipeline = pipeline

    def __init__(self):
        super().__init__()
        self.branches = None
        self.pipelines = None
        self.default_pipeline = None
        self.args = None

    def __repr__(self):
        return 'case()'

    # AbstractOp

    def setup(self, env):
        def pipeline(pipeline):
            # PyCharm sees a syntax error (on references to marcel.pipeline.Pipeline and
            # marcel.exception) without these?!
            import marcel.core
            import marcel.exception
            try:
                if not isinstance(pipeline, marcel.pipeline.Pipeline):
                    raise marcel.exception.KillCommandException(f'Expected pipeline, found {arg}')
                pipeline.setup(env)
                return pipeline
            except Exception as e:
                raise marcel.exception.KillCommandException(f'Expected pipeline, found {arg}')

        self.pipelines = []
        if len(self.args) < 2:
            raise marcel.exception.KillCommandException('case requires at least 2 arguments')
        # Functions and args alternate. For the API, pipelines can show up as functions, so testing to distinguish
        # between functions and pipelines cannot be perfect here, have to wait until execution to be sure.
        self.branches = []
        predicate = None
        for a in range(len(self.args) & ~1):
            arg = self.args[a]
            if predicate is None:
                if callable(arg):
                    predicate = arg
                else:
                    raise marcel.exception.KillCommandException(f'Expected function, found {arg}')
            else:
                self.branches.append(Case.Branch(predicate, pipeline(arg)))
                predicate = None
        if len(self.args) & 1 == 1:
            self.default_pipeline = pipeline(self.args[-1])

    def receive(self, env, x):
        pipeline = self.default_pipeline
        for branch in self.branches:
            px = self.call(env, branch.predicate, *x)
            if px:
                pipeline = branch.pipeline
                break
        if pipeline:
            pipeline.receive(env, x)

    def flush(self, env):
        for branch in self.branches:
            branch.pipeline.flush(env)
        if self.default_pipeline:
            self.default_pipeline.flush(env)
        self.propagate_flush(env)

    def cleanup(self):
        for branch in self.branches:
            branch.pipeline.cleanup()
        if self.default_pipeline:
            self.default_pipeline.cleanup()

    def ensure_functions_compiled(self, globals):
        for branch in self.branches:
            self.ensure_function_compiled(branch.predicate, globals)
        for pipeline in self.pipelines:
            pipeline.ensure_functions_compiled(globals)
        if self.default_pipeline:
            self.default_pipeline.ensure_functions_compiled(globals)

    # Internal

    def customize_pipelines(self, env):
        def redirect():
            return marcel.op.redirect.Redirect(self)

        if self.default_pipeline:
            self.default_pipeline = self.default_pipeline.append_immutable(redirect())
        for branch in self.branches:
            branch.pipeline = branch.pipeline.append_immutable(redirect())
