import requests
import json

# 测试导入到认证测试系统 (ID: 4)
url = "http://localhost:8000/api/systems/4/nodes/batch"

# 测试数据
data = {
    "nodes": [
        {"name": "测试节点1", "type": "组件", "insertID": "TEST001"},
        {"name": "测试节点2", "type": "服务器", "insertID": "TEST002"}
    ]
}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
