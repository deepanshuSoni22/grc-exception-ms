import sqlite3, hashlib

db = sqlite3.connect('grc.db')
db.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'admin'
)""")

pw = hashlib.sha256('admin123'.encode()).hexdigest()
db.execute('INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?,?,?)', ('admin', pw, 'admin'))
db.commit()
print('users table ready, admin user ensured')
db.close()
