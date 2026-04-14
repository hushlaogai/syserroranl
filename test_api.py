# 测试批量导入 API
import requests
import json

# 测试导入
data = [{"name": "测试节点", "type": "组件", "insertID": "TEST999"}]
response = requests.post(
    "http://localhost:8000/api/systems/3/nodes/batch",
    json={"nodes": data}
)
print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")
