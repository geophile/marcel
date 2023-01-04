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

import pathlib

import marcel.argsparser
import marcel.core
import marcel.exception
import marcel.main
import marcel.object.file
import marcel.opmodule
import marcel.op.bash
import marcel.op.filenames
import marcel.op.forkmanager
import marcel.util

File = marcel.object.file.File

HELP = '''
{L,wrap=F}upload CLUSTER DIR FILENAME ...

{L,indent=4:28}{r:CLUSTER}                 The cluster to which files will be uploaded.

{L,indent=4:28}{r:DIR}                     The directory on each cluster node to receive uploaded files.

{L,indent=4:28}{r:FILENAME}                A filename or glob pattern.

Copies local files to the indicated directory on each node of a cluster. The output stream is empty.

The files to be copied are specified by one or more {r:FILENAME}s. Each
{r:FILENAME} is a file name or a glob pattern.

{r:CLUSTER} must be configured for marcel, (run {n:help cluster} for
information on configuring clusters).

{r:DIR} must be an absolute path, corresponding to a pre-exising directory
on each node of the {r:CLUSTER}. The user configured for cluster access
must have permission to write to the directory.
'''


def upload(env, cluster, dir, *paths):
    return Upload(env), [cluster, dir] + list(paths)


class UploadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('upload', env)
        self.add_anon('cluster', convert=self.cluster)
        self.add_anon('dir', convert=self.check_str_or_file, target='dir_arg')
        self.add_anon_list('filenames', convert=self.check_str_or_file, target='filenames_arg')
        self.validate()


class Upload(marcel.core.Op):

    SCP_COMMAND = 'scp -Cpqr -i {identity} {sources} {user}@{host}:{dest}'

    def __init__(self, env):
        super().__init__(env)
        self.cluster = None
        self.dir_arg = None
        self.dir = None
        self.filenames_arg = None
        self.filenames = None
        self.fork_manager = None

    def __repr__(self):
        return f'upload({self.filenames_arg} -> {self.cluster}:{self.dir_arg})'

    def setup(self):
        self.dir = self.eval_function('dir_arg',
                                      str,
                                      pathlib.Path, pathlib.PosixPath, File)
        self.dir = pathlib.Path(self.dir)
        if not self.dir.is_absolute():
            raise marcel.exception.KillCommandException(f'Target directory must be absolute: {self.dir}')
        self.filenames = self.eval_function('filenames_arg',
                                            str, pathlib.Path, pathlib.PosixPath, File)
        self.filenames = marcel.op.filenames.Filenames(self.env(), self.filenames).normalize()
        if len(self.filenames) == 0:
            raise marcel.exception.KillCommandException(f'No qualifying paths, (possibly due to permission errors):'
                                                        f' {self.filenames}')
        # Empty pipeline will be filled in by customize_pipeline
        pipeline_template = marcel.core.Pipeline()
        pipeline_template.set_error_handler(self.owner.error_handler)
        self.fork_manager = marcel.op.forkmanager.ForkManager(op=self,
                                                              thread_ids=self.cluster.hosts,
                                                              pipeline_arg=pipeline_template,
                                                              max_pipeline_args=0,
                                                              customize_pipeline=self.customize_pipeline)
        self.fork_manager.setup()

    def run(self):
        self.fork_manager.run()

    @staticmethod
    def scp_command(identity, sources, user, host, dest):
        sources = marcel.util.quote_files(sources)
        return Upload.SCP_COMMAND.format(identity=identity,
                                         sources=sources,
                                         user=user,
                                         host=host,
                                         dest=dest)

    def customize_pipeline(self, pipeline, host):
        host_pipeline = pipeline.copy()
        scp_command = Upload.scp_command(host.identity, self.filenames, host.user, host.name, self.dir)
        host_pipeline.append(marcel.opmodule.create_op(self.env(), 'bash', scp_command))
        return host_pipeline
