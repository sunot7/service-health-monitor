import sqlite3
from contextlib import contextmanager

FIELDS = ('name', 'url', 'timestamp', 'status_code', 'success', 'response_time_ms', 'error')


@contextmanager
def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('''CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT,
            timestamp TEXT NOT NULL, status_code INTEGER, success INTEGER NOT NULL,
            response_time_ms REAL NOT NULL, error TEXT)''')
        with connection:
            yield connection
    finally:
        connection.close()


def save_result(database_path, row):
    with connect(database_path) as db:
        db.execute('INSERT INTO checks (' + ','.join(FIELDS) + ') VALUES (?,?,?,?,?,?,?)',
                   tuple(row.get(field) for field in FIELDS))


def rows(cursor):
    result = []
    for record in cursor:
        row = {field: record[field] for field in FIELDS}
        row['success'] = bool(row['success'])
        result.append(row)
    return result


def history(database_path, limit=100):
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError('limit must be a positive integer')
    with connect(database_path) as db:
        return rows(db.execute('SELECT * FROM checks ORDER BY timestamp DESC, id DESC LIMIT ?', (limit,)))


def latest(database_path):
    with connect(database_path) as db:
        return rows(db.execute('''SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY name ORDER BY timestamp DESC, id DESC) AS rank
            FROM checks) WHERE rank = 1 ORDER BY name'''))
