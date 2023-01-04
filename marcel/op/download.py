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
{L,wrap=F}download DIR CLUSTER FILENAME ...

{L,indent=4:28}{r:DIR}                     The local directory to which files will be downloaded.

{L,indent=4:28}{r:CLUSTER}                 The cluster from which files will be downloaded.

{L,indent=4:28}{r:FILENAME}                A remote filename or glob pattern.

Copies remote files from each node of a cluster, to a local directory. The output stream is empty.

{r:DIR} must be a pre-exising directory.

{r:CLUSTER} must be configured for marcel, (run {n:help cluster} for
information on configuring clusters).

The files to be copied are specified by one or more {r:FILENAME}s. Each
{r:FILENAME} is a file name or a glob pattern, and must be an absolute path, (i.e., it must start with /).
Files from host {n:H} will be downloaded to the directory {n:DIR/H}. 
'''


def download(env, dir, cluster, *paths):
    return Download(env), [dir, cluster] + list(paths)


class DownloadArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('download', env)
        self.add_anon('dir', convert=self.check_str_or_file, target='dir_arg')
        self.add_anon('cluster', convert=self.cluster)
        self.add_anon_list('filenames', convert=self.check_str_or_file, target='filenames_arg')
        self.validate()


class Download(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.dir_arg = None
        self.dir = None
        self.cluster = None
        self.filenames_arg = None
        self.filenames = None
        self.fork_manager = None

    def __repr__(self):
        return f'download({self.dir_arg} <- {self.cluster} {self.filenames_arg})'

    def setup(self):
        self.dir = self.eval_function('dir_arg',
                                      str,
                                      pathlib.Path, pathlib.PosixPath, File)
        self.dir = pathlib.Path(self.dir)
        self.dir = marcel.op.filenames.Filenames(self.env(), [self.dir]).normalize()
        if len(self.dir) == 0:
            raise marcel.exception.KillCommandException(f'Target directory does not exist: {self.dir_arg}')
        else:
            self.dir = self.dir[0]
        self.filenames = self.eval_function('filenames_arg',
                                            str, pathlib.Path, pathlib.PosixPath, File)
        if len(self.filenames) == 0:
            raise marcel.exception.KillCommandException('No remote files specified')
        for filename in self.filenames:
            if not filename.startswith('/'):
                raise marcel.exception.KillCommandException(f'Remote filenames must be absolute: {filename}')
        # Empty pipeline will be filled in by customize_pipeline
        pipeline_template = marcel.core.Pipeline()
        pipeline_template.set_error_handler(self.owner.error_handler)
        self.fork_manager = marcel.op.forkmanager.ForkManager(op=self,
                                                              thread_ids=self.cluster.hosts,
                                                              pipeline_arg=pipeline_template,
                                                              max_pipeline_args=0,
                                                              customize_pipeline=self.customize_pipeline)
        self.fork_manager.setup()
        self.ensure_node_directories_exist()

    def run(self):
        self.fork_manager.run()

    @staticmethod
    def scp_command(identity, sources, host, dest):
        scp_command = ['scp', '-Cpqr', '-i', identity]
        for source in sources:
            scp_command.append(f'{host.user}@{host.name}:{marcel.util.quote_files(source)}')
        node_dir = dest / host.name
        scp_command.append(node_dir.as_posix())
        return ' '.join(scp_command)

    def customize_pipeline(self, pipeline, host):
        host_pipeline = pipeline.copy()
        scp_command = Download.scp_command(host.identity, self.filenames, host, self.dir)
        host_pipeline.append(marcel.opmodule.create_op(self.env(), 'bash', scp_command))
        return host_pipeline

    def ensure_node_directories_exist(self):
        for host in self.cluster:
            host_dir = self.dir / host.name
            host_dir.mkdir(exist_ok=True)
