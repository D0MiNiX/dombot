import sqlite3 as dbs


class Database:
    def __init__(self, db):
        self.db = db
        self.connection = dbs.connect(db, isolation_level=None)
        self.cursor = self.connection.cursor()

    def query(self, query, row_count=False):
        try:
            self.cursor.execute(query)
            if row_count:
                return self.cursor.rowcount
            return None
        except Exception as e:
            return e

    def select(self, query):
        try:
            self.cursor.execute(query)
            return self.cursor
        except Exception as e:
            return e

    def select_single(self, query):
        try:
            self.cursor.execute(query)
            res = self.cursor.fetchone()
            if res is not None:
                return res[0]
            else:
                return Exception("no results fetched")
        except Exception as e:
            return e

    def insert(self, table, values):
        try:
            data = ", ".join(map(lambda _: '?', values))
            query = f"INSERT INTO `{table}` VALUES ({data})"
            self.cursor.execute(query, tuple(values))
            return None
        except Exception as e:
            return e
    
    def delete(self, table, column, value):
        try:
            data = (value,)
            query = f"DELETE FROM `{table}` WHERE {column}=?"
            self.cursor.execute(query, data)
            return self.cursor.rowcount
        except Exception as e:
            return e
    
    def close_all(self):
        self.cursor.close()
        self.connection.close()
