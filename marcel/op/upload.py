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

# import multiprocessing as mp
#
# import dill
#
# import marcel.argsparser
# import marcel.core
# import marcel.exception
# import marcel.opmodule
# import marcel.op.labelthread
#
#
# HELP = '''
# {L,wrap=F}upload CLUSTER:DIR FILENAME ...
#
# {L,indent=4:28}{r:CLUSTER}                 The cluster to which files will be uploaded.
#
# {L,indent=4:28}{r:DIR}                     The directory on each cluster node to receive uploaded files.
#
# {L,indent=4:28}{r:FILENAME}                A filename or glob pattern.
#
# Copies local files to the indicated directory on each node of a cluster.
#
# The files to be copied are specified by one or more FILENAMEs. Each
# FILENAME is a file name or a glob pattern.
#
# CLUSTER must be configured for marcel, (run "help cluster" for
# information on configuring clusters).
#
# DIR must be an absolute path, corresponding to a pre-exising directory
# on each node of the CLUSTER. The user configured for cluster access
# must have permission to write to the directory.
# '''
#
#
# def upload(env, cluster, dir, *paths):
#     return Upload(env), [cluster, dir, paths]
#
#
# class UploadArgsParser(marcel.argsparser.ArgsParser):
#
#     def __init__(self, env):
#         super().__init__('fork', env)
#         self.add_anon('cluster_dir')
#         self.add_anon_list('paths')
#         self.validate()
#
#
# class Upload(marcel.core.Op):
#
#     def __init__(self, env):
#         super().__init__(env)
#         self.cluster_dir = None
#         self.paths = None
#         self.cluster_name = None
#         self.dir = None
#         self.pipeline = None
#
#     def __repr__(self):
#         return f'upload {self.cluster}:{self.dir} {self.paths}'
#
#     # AbstractOp
#
#     def setup(self):
#         colon = self.cluster_dir.find(':')
#         if colon < 1 or colon == len(self.cluster_dir) - 1:
#             raise marcel.exception.KillCommandException(f'Invalid specification of CLUSTER:DIR: {self.cluster_dir}')
#         self.cluster_name = self.cluster_dir[:colon]
#         self.dir = self.cluster_dir[colon + 1:]
#         self.pipeline = self.create_pipeline()
#
#     # Op
#
#     def run(self):
#         for worker in self.workers:
#             worker.start_process()
#         for worker in self.workers:
#             worker.wait()
#
#     def must_be_first_in_pipeline(self):
#         return True
#
#     # Implementation
#     def create_pipeline(self):
#         # [fork CLUSTER [bash rsync -asz -i CLUSTER.identity PATHS host:DIR]], for each host in CLUSTER
#         rsync_pipeline = marcel.core.Pipeline()
#         cluster = self.env().cluster(self.cluster_name)
#         host_dir =
#         if cluster is None:
#             raise marcel.exception.KillCommandException(f'There is no cluster named {self.cluster_name}')
#         bash_op = marcel.opmodule.create_op(self.env(), 'bash',
#                                             'rsync',
#                                             '-asz',
#                                             '-i',
#                                             cluster.identity,
#                                             *self.paths,
#                                             host_dir)
#         fork_pipeline = marcel.core.Pipeline()
#         fork_op = marcel.opmodule.create_op(self.env(), 'fork', self.cluster, rsync_pipeline)
#         return fork_pipeline
#
# class ForkWorker:
#
#     class SendToParent(marcel.core.Op):
#
#         def __init__(self, env, parent):
#             super().__init__(env)
#             self.parent = parent
#
#         def __repr__(self):
#             return 'sendtoparent()'
#
#         def receive(self, x):
#             self.parent.send(dill.dumps(x))
#
#         def receive_error(self, error):
#             self.parent.send(dill.dumps(error))
#
#     def __init__(self, host, op):
#         self.host = host
#         self.op = op
#         self.process = None
#         # duplex=False: child writes to parent when function completes execution. No need to communicate in the
#         # other direction
#         self.reader, self.writer = mp.Pipe(duplex=False)
#         self.pipeline = marcel.core.Pipeline()
#         remote = marcel.opmodule.create_op(op.env(), 'remote', op.pipeline)
#         remote.set_host(host)
#         label_thread = marcel.op.labelthread.LabelThread(op.env())
#         label_thread.set_label(host)
#         send_to_parent = ForkWorker.SendToParent(self.op.env(), self.writer)
#         self.pipeline.append(remote)
#         self.pipeline.append(label_thread)
#         self.pipeline.append(send_to_parent)
#         label_thread.receiver = op.receiver
#
#     def start_process(self):
#         def run_pipeline_in_child():
#             try:
#                 self.pipeline.set_error_handler(self.op.owner.error_handler)
#                 self.pipeline.setup()
#                 self.pipeline.set_env(self.op.env())
#                 self.pipeline.run()
#                 self.pipeline.flush()
#                 self.pipeline.cleanup()
#             except BaseException as e:
#                 self.writer.send(dill.dumps(e))
#             self.writer.close()
#         self.process = mp.Process(target=run_pipeline_in_child, args=tuple())
#         self.process.daemon = True
#         self.process.start()
#         self.writer.close()
#
#     def wait(self):
#         try:
#             while True:
#                 input = self.reader.recv()
#                 x = dill.loads(input)
#                 self.op.send(x)
#         except EOFError:
#             pass
#         while self.process.is_alive():
#             self.process.join(0.1)
