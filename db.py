from os import environ as env
import psycopg2
import sqlite3
from urllib.parse import urlparse


class DBContextManager:
    def __enter__(self):
        if 'DATABASE_URL' in env:
            url = urlparse(env['DATABASE_URL'])
            self.conn = psycopg2.connect(
                dbname=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port,
            )
        else:
            self.conn = sqlite3.connect('toons.db')

        return self.conn

    def __exit__(self, type_, value, traceback):
        if not value:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
