# -*- coding: utf-8 -*-
"""批量添加测试数据的脚本"""
import requests
import json
import time
import sys

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8080"

def create_node(name, node_type, description=""):
    """创建节点"""
    resp = requests.post(f"{BASE_URL}/api/nodes", json={
        "name": name,
        "type": node_type,
        "description": description
    })
    if resp.status_code == 201:
        data = resp.json()
        print(f"[OK] Create node: {name} (ID: {data['id']})")
        return data['id']
    else:
        print(f"[FAIL] Create node: {name} - {resp.text}")
        return None

def create_edge(source_id, target_id, weight, description=""):
    """创建边"""
    resp = requests.post(f"{BASE_URL}/api/edges", json={
        "source_id": source_id,
        "target_id": target_id,
        "weight": weight,
        "description": description
    })
    if resp.status_code == 201:
        print(f"  [OK] Create edge: {source_id} -> {target_id} (weight: {weight})")
        return True
    else:
        print(f"  [FAIL] Create edge: {source_id} -> {target_id} - {resp.text}")
        return False

def main():
    print("=" * 50)
    print("syserroranl 测试数据生成器")
    print("=" * 50)
    
    # 清理现有数据
    print("\n正在清理现有数据...")
    resp = requests.get(f"{BASE_URL}/api/nodes")
    if resp.status_code == 200:
        for node in resp.json():
            requests.delete(f"{BASE_URL}/api/nodes/{node['id']}")
    print("清理完成")
    
    # 创建节点
    print("\n" + "-" * 50)
    print("创建节点...")
    
    nodes = {}
    
    # 服务系统
    nodes['mobile_app'] = create_node("移动端APP", "服务系统", "面向C端用户的移动应用")
    nodes['web_portal'] = create_node("Web门户", "服务系统", "面向用户的Web站点")
    
    # 系统功能
    nodes['auth_api'] = create_node("认证API", "系统功能", "提供用户认证服务")
    nodes['user_api'] = create_node("用户API", "系统功能", "提供用户CRUD服务")
    
    # 系统
    nodes['auth_system'] = create_node("认证中心", "系统", "统一身份认证服务")
    nodes['user_system'] = create_node("用户中心", "系统", "用户管理服务")
    
    # 支撑系统
    nodes['mysql_db'] = create_node("MySQL数据库", "支撑系统", "关系型数据存储")
    nodes['redis_cache'] = create_node("Redis缓存", "支撑系统", "缓存服务")
    nodes['k8s_cluster'] = create_node("K8S集群", "支撑系统", "容器编排平台")
    
    # 节点
    nodes['auth_node'] = create_node("认证服务节点", "节点", "认证服务集群")
    nodes['user_node'] = create_node("用户服务节点", "节点", "用户服务集群")
    
    # 集群
    nodes['auth_primary'] = create_node("认证主集群", "集群", "认证服务主集群")
    nodes['auth_standby'] = create_node("认证备集群", "集群", "认证服务备集群")
    nodes['user_primary'] = create_node("用户主集群", "集群", "用户服务主集群")
    
    # 服务器
    nodes['server_1'] = create_node("APP-SRV-01", "服务器", "应用服务器01")
    nodes['server_2'] = create_node("APP-SRV-02", "服务器", "应用服务器02")
    nodes['server_3'] = create_node("APP-SRV-03", "服务器", "应用服务器03")
    nodes['db_server_1'] = create_node("DB-SRV-01", "服务器", "数据库服务器01")
    
    # 组件
    nodes['nginx'] = create_node("Nginx", "组件", "反向代理/负载均衡")
    nodes['tomcat'] = create_node("Tomcat", "组件", "Java应用容器")
    nodes['spring_boot'] = create_node("Spring Boot", "组件", "Java应用框架")
    nodes['mysql'] = create_node("MySQL Server", "组件", "数据库引擎")
    nodes['redis'] = create_node("Redis Server", "组件", "缓存引擎")
    nodes['k8s_pod'] = create_node("K8S Pod", "组件", "容器编排单元")
    
    # 创建边（依赖关系）
    print("\n" + "-" * 50)
    print("创建依赖关系...")
    
    # 服务系统 → 系统功能
    create_edge(nodes['mobile_app'], nodes['auth_api'], 8, "APP调用认证API")
    create_edge(nodes['mobile_app'], nodes['user_api'], 8, "APP调用用户API")
    create_edge(nodes['web_portal'], nodes['auth_api'], 8, "门户调用认证API")
    create_edge(nodes['web_portal'], nodes['user_api'], 8, "门户调用用户API")
    
    # 系统功能 → 系统
    create_edge(nodes['auth_api'], nodes['auth_system'], 10, "认证API依赖认证中心")
    create_edge(nodes['user_api'], nodes['user_system'], 10, "用户API依赖用户中心")
    
    # 系统 → 节点
    create_edge(nodes['auth_system'], nodes['auth_node'], 9, "认证系统部署在认证节点")
    create_edge(nodes['user_system'], nodes['user_node'], 9, "用户系统部署在用户节点")
    
    # 节点 → 集群
    create_edge(nodes['auth_node'], nodes['auth_primary'], 7, "认证节点包含主集群")
    create_edge(nodes['auth_node'], nodes['auth_standby'], 5, "认证节点包含备集群")
    create_edge(nodes['user_node'], nodes['user_primary'], 7, "用户节点包含主集群")
    
    # 集群 → 服务器
    create_edge(nodes['auth_primary'], nodes['server_1'], 6, "主集群包含服务器1")
    create_edge(nodes['auth_primary'], nodes['server_2'], 6, "主集群包含服务器2")
    create_edge(nodes['auth_standby'], nodes['server_3'], 3, "备集群包含服务器3")
    create_edge(nodes['user_primary'], nodes['server_1'], 6, "用户主集群使用服务器1")
    create_edge(nodes['user_primary'], nodes['server_2'], 6, "用户主集群使用服务器2")
    
    # 服务器 → 组件
    create_edge(nodes['server_1'], nodes['nginx'], 5, "服务器运行Nginx")
    create_edge(nodes['server_1'], nodes['tomcat'], 7, "服务器运行Tomcat")
    create_edge(nodes['server_2'], nodes['nginx'], 5, "服务器运行Nginx")
    create_edge(nodes['server_2'], nodes['tomcat'], 7, "服务器运行Tomcat")
    create_edge(nodes['server_3'], nodes['nginx'], 5, "服务器运行Nginx")
    create_edge(nodes['server_3'], nodes['tomcat'], 7, "服务器运行Tomcat")
    create_edge(nodes['db_server_1'], nodes['mysql'], 10, "数据库服务器运行MySQL")
    create_edge(nodes['db_server_1'], nodes['redis'], 9, "数据库服务器运行Redis")
    
    # 组件 → 支撑系统
    create_edge(nodes['mysql'], nodes['mysql_db'], 10, "MySQL组件依赖MySQL数据库服务")
    create_edge(nodes['redis'], nodes['redis_cache'], 9, "Redis组件依赖Redis缓存服务")
    create_edge(nodes['tomcat'], nodes['k8s_cluster'], 8, "Tomcat运行在K8S集群")
    
    # 打印统计
    print("\n" + "=" * 50)
    resp = requests.get(f"{BASE_URL}/api/stats")
    if resp.status_code == 200:
        stats = resp.json()
        print(f"[OK] Data generation complete!")
        print(f"  - Total nodes: {stats['total_nodes']}")
        print(f"  - Total edges: {stats['total_edges']}")
        print(f"  - Nodes by type: {stats['nodes_by_type']}")

if __name__ == "__main__":
    main()
