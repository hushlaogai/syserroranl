"""为已存在的节点表添加 insertID 字段"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'syserroranl.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 获取所有系统
c.execute('SELECT id FROM systems')
systems = c.fetchall()

for (system_id,) in systems:
    table_name = f'nodes_system_{system_id}'
    # 检查列是否存在
    c.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in c.fetchall()]
    
    if 'insertID' not in columns:
        print(f"添加 insertID 到 {table_name}...")
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN insertID VARCHAR(255)")
    else:
        print(f"{table_name} 已有 insertID 字段")

conn.commit()
conn.close()
print("完成！")
