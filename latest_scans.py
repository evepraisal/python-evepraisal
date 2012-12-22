import sqlite3
import humanize
import datetime

if __name__ == "__main__":
    conn = sqlite3.connect('data/scans.db')
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT Id, Created FROM Scans ORDER BY Created DESC, Id DESC LIMIT 20;")
        for result in cur.fetchall():
            _id, _timestamp = result
            _created = "unknown"
            if _timestamp:
                _created = humanize.naturaltime(datetime.datetime.fromtimestamp(_timestamp))
            print("scan_id: %s, created: %s" % (_id, _created))
