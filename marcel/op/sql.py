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
import marcel.object.db

HELP = '''
{L,wrap=F}sql [-d|--db DB_PROFILE] [-c|--commit UPDATE_COUNT] [-a|--autocommit] 
[-u|--update-counts] STATEMENT [ARG ...]

{L,indent=4:28,wrap=T}{r:-d}, {r:--db}                Access the database whose profile is named 
{r:DB_PROFILE}, in {n:~/.marcel.py}. If omitted, use the default profile, specified by the 
environment variable {n:DB_DEFAULT}.

{L,indent=4:28}{r:-c}, {r:--commit}            Commit after {r:UPDATE_COUNT} rows have been updated, 
as indicated by the sum of update counts returned in response to SQL statements such as 
INSERT, UPDATE, DELETE.

{L,indent=4:28}{r:-a}, {r:--autocommit}        Run in auto-commit mode. I.e., every SQL statement 
runs in its own implicit transaction.

{L,indent=4:28}{r:-u}, {r:--update-counts}     Write update counts to output stream. 
(Default behavior is to not write update counts.)

{L,indent=4:28}{r:STATEMENT}               A SQL statement. Consistent with Python's DBAPI specification,
parameters are indicated using %s.

{L,indent=4:28}{r:ARG}                     A value to be bound to a variable in a SQL statement.

SQL statements may have parameters, which are indicated by %s. There are two ways in which values are bound to
these arguments:

{L}- If {r:ARG}s are specified, they are bound to the SQL statement's parameters.

{L}- If {r:ARG}s are not specified, then for each input tuple, the tuple's components are bound
to the SQL statement's parameters, and then the statement is executed.

If the SQL statement is {n:SELECT} then rows returned from the query are written to the output stream.
In other cases, the update count is written to the output stream.

Commit is handled in one of three ways:

{L}- {n:One commit}: Commit occurs at the end of the entire command. This means that for a long-running
command that does updates, no updates are visible until the command finishes execution. This is the default
behavior, (i.e., if neither {r:--commit} nor {r:--autocommit} are specified).

{L}- {n:Periodic commit}: The {r:--commit} flag specifies the commit frequency as an {r:UPDATE_COUNT}. 
Update counts from SQL statements are totalled, and when total equals or exceeds {r:UPDATE_COUNT}, 
a commit is performed, and the counter is reset to zero.

{L}- {n:Auto-commit}: If {r:--autocommit} is specified, then each SQL statement runs in its own implicit
transaction.

Note that the {r:--commit} and {r:--autocommit} flags are mutually exclusive.
'''


def sql(env, *args, db=None, autocommit=None, update_counts=None, commit=None):
    if len(args) == 0:
        raise marcel.exception.KillCommandException('No sql statement provided')
    statement = args[0]
    args = args[1:]
    op_args = []
    if autocommit:
        op_args.append('--autocommit')
    if update_counts:
        op_args.append('--update-counts')
    if commit is not None:
        op_args.extend(['--commit', commit])
    op_args.append(statement)
    if args:
        op_args.extend(args)
    op = Sql(env)
    op.db = db
    return Sql(env), op_args


class SqlArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('sql', env)
        self.add_flag_one_value('db', '-d', '--db', target='dbvar')
        self.add_flag_no_value('autocommit', '-a', '--autocommit')
        self.add_flag_no_value('update_counts', '-u', '--update-counts')
        self.add_flag_one_value('commit', '-c', '--commit', convert=self.str_to_int)
        self.add_anon('statement', target='statement_arg')
        self.add_anon_list('args', target='args_arg')
        self.at_most_one('autocommit', 'commit')
        self.validate()


class Sql(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.dbvar = None
        self.db = None
        self.autocommit = None
        self.update_counts = None
        self.commit = None
        self.statement_arg = None
        self.statement = None
        self.args_arg = None
        self.args = None
        self.connection = None
        self.delegate = None
        self.total_update_count = None

    def __repr__(self):
        return f'sql({self.statement})'

    # AbstractOp

    def setup(self):
        self.statement = self.eval_function('statement_arg', str)
        self.args = self.eval_function('args_arg')
        if self.commit is None:
            self.commit = 0  # Commit only in flush
        elif self.commit < 0:
            raise marcel.exception.KillCommandException(f'--commit value must be a positive integer: {self.commit}')
        self.total_update_count = 0
        env = self.env()
        if type(self.db) is not marcel.object.db.Database:
            # Interactive usage
            self.db = env.db(self.dbvar) if self.dbvar is not None else env.getvar('DB_DEFAULT')
            if self.db is None:
                raise marcel.exception.KillCommandException('No database profile defined')
        # else: API usage
        try:
            self.connection = self.db.connection()
        except Exception as e:
            raise marcel.exception.KillCommandException(
                f'Unable to connect to database {self.db.dbname} as {self.db.user}: {e}')
        if self.autocommit:
            self.connection.set_autocommit(True)
        self.delegate = self.classify_statement()(self.connection, self)

    def run(self):
        self.receive(None)

    def receive(self, x):
        try:
            self.delegate.receive(x)
        except Exception as e:
            self.connection.rollback()
            raise marcel.exception.KillCommandException(e)

    def flush(self):
        try:
            self.delegate.flush()
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise marcel.exception.KillCommandException(e)
        finally:
            self.connection.close()
            self.propagate_flush()

    # For use by this class

    def classify_statement(self):
        verb_start = 0
        while self.statement[verb_start].isspace():
            verb_start += 1
        verb_end = verb_start
        end = len(self.statement)
        while verb_end < end and not self.statement[verb_end].isspace():
            verb_end += 1
        verb = self.statement[verb_start:verb_end].lower()
        return (SqlSelect if verb == 'select' else
                SqlInsert if verb == 'insert' else
                SqlOther)


class SqlStatement:

    def __init__(self, connection, op):
        self.connection = connection
        self.op = op

    def receive(self, x):
        pass

    def flush(self):
        if self.op.autocommit is False:
            self.connection.commit()

    def commit_if_necessary(self, update_count):
        op = self.op
        if not op.autocommit and op.commit > 0:
            op.total_update_count += update_count
            if op.total_update_count >= op.commit:
                op.connection.commit()
                op.total_update_count = 0


class SqlSelect(SqlStatement):

    def __init__(self, connection, op):
        super().__init__(connection, op)

    def receive(self, x):
        op = self.op
        args = op.args if x is None else x
        for row in self.connection.query(op.statement, args):
            op.send(row)


class SqlInsert(SqlStatement):

    def __init__(self, connection, op):
        super().__init__(connection, op)

    def receive(self, x):
        op = self.op
        args = op.args if x is None else x
        update_count = self.connection.insert(op.statement, args)
        self.commit_if_necessary(update_count)
        if op.update_counts:
            op.send(update_count)


class SqlOther(SqlStatement):

    def __init__(self, connection, op):
        super().__init__(connection, op)

    def receive(self, x):
        op = self.op
        args = op.args if x is None else x
        update_count = self.connection.execute(op.statement, args)
        self.commit_if_necessary(update_count)
        if op.update_counts:
            op.send(update_count)
