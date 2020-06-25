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
{L,wrap=F}sql [-d|--db DB_PROFILE] [-c|--commit UPDATE_COUNT] [-a|--autocommit] STATEMENT [ARG ...]

{L,indent=4:28,wrap=T}{r:-d}, {r:--db}                Access the database whose profile is named 
{r:DB_PROFILE}, in {n:.marcel.py}. If omitted, use the default profile, specified by the 
environment variable {n:DB_DEFAULT}.

{L,indent=4:28}{r:-c}, {r:--commit}            Commit after {r:UPDATE_COUNT} rows have been updated, 
as indicated by the sum of update counts returned in response to SQL statements such as 
INSERT, UPDATE, DELETE.

{L,indent=4:28}{r:-a}, {r:--autocommit}        Run in auto-commit mode. I.e., every SQL statement 
runs in its own implicit transaction.

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


def sql(env, statement, *args, db=None, autocommit=None):
    op_args = []
    if db:
        op_args.extend(['--db', db])
    if autocommit:
        op_args.extend(['--autocommit', autocommit])
    op_args.append(statement)
    if args:
        op_args.extend(args)
    return Sql(env), op_args


class SqlArgsParser(marcel.argsparser.ArgsParser):

    def __init__(self, env):
        super().__init__('sql', env)
        self.add_flag_one_value('db', '-d', '--db')
        self.add_flag_no_value('autocommit', '-a', '--autocommit')
        self.add_flag_one_value('commit', '-c', '--commit', convert=self.str_to_int)
        self.add_anon('statement')
        self.add_anon_list('args')
        self.at_most_one('autocommit', 'commit')
        self.validate()


class Sql(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.db = None
        self.autocommit = None
        self.commit = None
        self.statement = None
        self.args = None
        self.connection = None
        self.delegate = None
        self.commit_count = None

    def __repr__(self):
        return f'sql({self.statement})'

    # AbstractOp

    def setup_1(self):
        self.eval_function('statement', str)
        self.eval_function('args')
        if self.commit is None:
            self.commit = 0  # Commit only in receive_complete
        elif self.commit <= 0:
            raise marcel.exception.KillCommandException(f'--commit value must be a positive integer: {self.commit}')
        self.commit_count = 0
        db_profile = self.env().getvar('DB_DEFAULT') if self.db is None else self.db
        if db_profile is None:
            raise marcel.exception.KillCommandException('No database profile defined')
        db = self.env().db(db_profile)
        self.connection = db.connection()
        if self.autocommit:
            self.connection.set_autocommit(True)
        if db is None:
            raise marcel.exception.KillCommandException(f'No database profile named {db_profile}')
        self.delegate = self.classify_statement()(self.connection, self)

    def receive(self, x):
        try:
            self.delegate.receive(x)
        except Exception as e:
            self.connection.rollback()
            raise marcel.exception.KillCommandException(e)

    def receive_complete(self):
        try:
            self.delegate.receive_complete()
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise marcel.exception.KillCommandException(e)

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

    def receive_complete(self):
        if self.op.autocommit is False:
            self.connection.commit()

    def commit_if_necessary(self, update_count):
        op = self.op
        if op.autocommit is False and op.commit > 0:
            op.commit_count += update_count
            if op.commit_count >= op.commit:
                op.connection.commit()
                op.commit_count = 0


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
        op.send(update_count)


class SqlOther(SqlStatement):

    def __init__(self, connection, op):
        super().__init__(connection, op)

    def receive(self, x):
        op = self.op
        args = op.args if x is None else x
        update_count = self.connection.execute(op.statement, args)
        self.commit_if_necessary(update_count)
        op.send(update_count)
