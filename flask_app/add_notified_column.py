import sqlite3

db = sqlite3.connect('grc.db')
try:
    db.execute('ALTER TABLE exceptions ADD COLUMN last_notified TEXT DEFAULT NULL')
    db.commit()
    print('last_notified column added successfully')
except Exception as e:
    print('Result:', e)
db.close()
