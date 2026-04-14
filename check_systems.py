import sqlite3

conn = sqlite3.connect('syserroranl.db')
c = conn.cursor()

# 查看所有系统
c.execute('SELECT id, name FROM systems')
systems = c.fetchall()
print("系统中的所有系统:")
for s in systems:
    print(f"  ID: {s[0]}, Name: {s[1]}")

# 查看所有节点表
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'nodes_%'")
tables = c.fetchall()
print("\n节点表:")
for t in tables:
    print(f"  {t[0]}")

conn.close()
