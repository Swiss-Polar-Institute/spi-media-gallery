import sqlite3

from django.conf import settings


class DatetimeToPosition(object):
    def __init__(self):
        database_path = settings.DATETIME_POSITIONS_SQLITE3_PATH

        uri = 'file:{}?mode=ro'.format(database_path)
        conn = sqlite3.connect(uri, uri=True)

        self.sqlite3_cur = conn.cursor()

        self.sqlite3_cur.execute('PRAGMA case_sensitive_like = 1')

    def lookup_datetime_datetime(self, datetime_datetime):
        return self.lookup_datetime_text(datetime_datetime.strftime('%Y-%m-%dT%H:%M:%S'))

    def lookup_datetime_text(self, datetime_text):
        one_sec_approximation = datetime_text + '%'
        self.sqlite3_cur.execute('SELECT latitude,longitude FROM gps WHERE date_time LIKE ?', (one_sec_approximation,))

        result = self.sqlite3_cur.fetchone()

        if result is None:
            return None
        else:
            return float(result[0]), float(result[1])
